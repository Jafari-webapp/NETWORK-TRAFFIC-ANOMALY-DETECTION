from datetime import datetime, timedelta, timezone

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models.anomaly_result import AnomalyResult
from app.models.firewall_log import FirewallLog
from app.models.llm_analysis import LLMAnalysis
from app.models.upload_history import UploadHistory

COMBINED_WINDOW_DAYS = 30  # "Combined Insights" = uploads still within the 1-month Upload History retention


def latest_upload_id(db: Session) -> int | None:
    row = db.query(UploadHistory.id).order_by(UploadHistory.uploaded_at.desc()).limit(1).one_or_none()
    return row[0] if row else None


def resolve_upload_ids(db: Session, upload_id: int | None, scope: str) -> list[int] | None:
    """
    Returns a list of upload_history_id values to filter FirewallLog by, or
    None to mean "no upload filter" (used for 'all', which already only shows
    whatever the retention policy has kept).

    - upload_id given -> exactly that one upload ("View Insights")
    - scope == "combined" -> every upload still within the Upload History
      retention window ("Combined Insights")
    - scope == "all" -> no filter at all ("All Insights")
    - otherwise (default "latest") -> just the most recently uploaded batch
    """
    if upload_id is not None:
        return [upload_id]

    if scope == "all":
        return None

    if scope == "combined":
        cutoff = datetime.now(timezone.utc) - timedelta(days=COMBINED_WINDOW_DAYS)
        rows = db.query(UploadHistory.id).filter(UploadHistory.uploaded_at >= cutoff).all()
        return [r[0] for r in rows]

    # default: "latest" — the most recent single upload only
    latest = latest_upload_id(db)
    return [latest] if latest is not None else []


def _apply_upload_filter(query, upload_ids: list[int] | None):
    if upload_ids is None:
        return query
    if not upload_ids:
        # No uploads yet — return a query that matches nothing, rather than
        # accidentally showing unfiltered/all data.
        return query.filter(FirewallLog.id.is_(None))
    return query.filter(FirewallLog.upload_history_id.in_(upload_ids))


def get_summary(db: Session, upload_ids: list[int] | None = None) -> dict:
    log_q = _apply_upload_filter(db.query(FirewallLog), upload_ids)
    total_logs = log_q.count()

    anomaly_q = (
        db.query(AnomalyResult.severity, func.count(AnomalyResult.id))
        .join(FirewallLog, AnomalyResult.firewall_log_id == FirewallLog.id)
        .filter(AnomalyResult.is_anomaly.is_(True))
    )
    anomaly_q = _apply_upload_filter(anomaly_q, upload_ids)
    severity_counts = dict(anomaly_q.group_by(AnomalyResult.severity).all())
    total_anomalies = sum(severity_counts.values())

    ip_q = _apply_upload_filter(db.query(FirewallLog), upload_ids)
    unique_src_ips = ip_q.with_entities(func.count(func.distinct(FirewallLog.src_ip))).scalar() or 0
    ip_q2 = _apply_upload_filter(db.query(FirewallLog), upload_ids)
    unique_dst_ips = ip_q2.with_entities(func.count(func.distinct(FirewallLog.dst_ip))).scalar() or 0

    return {
        "total_logs": total_logs,
        "total_anomalies": total_anomalies,
        "normal_logs": max(total_logs - total_anomalies, 0),
        "low_severity": severity_counts.get("LOW", 0),
        "medium_severity": severity_counts.get("MEDIUM", 0),
        "high_severity": severity_counts.get("HIGH", 0),
        "critical_severity": severity_counts.get("CRITICAL", 0),
        "unique_src_ips": unique_src_ips,
        "unique_dst_ips": unique_dst_ips,
        "anomaly_rate": round((total_anomalies / total_logs) * 100, 2) if total_logs else 0.0,
    }


def get_recent_anomalies(
    db: Session, limit: int = 20, upload_ids: list[int] | None = None, hours: int | None = 24,
) -> list[dict]:
    query = (
        db.query(AnomalyResult, FirewallLog, LLMAnalysis)
        .join(FirewallLog, AnomalyResult.firewall_log_id == FirewallLog.id)
        .outerjoin(LLMAnalysis, LLMAnalysis.anomaly_id == AnomalyResult.id)
        .filter(AnomalyResult.is_anomaly.is_(True))
    )
    query = _apply_upload_filter(query, upload_ids)
    if hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        # detected_at = when the ML pipeline processed this row (upload/processing
        # time), not the log's own event timestamp — so "recent" always reflects
        # what was actually uploaded in the last N hours, even if the underlying
        # CSV contains older historical traffic timestamps.
        query = query.filter(AnomalyResult.detected_at >= cutoff)

    rows = query.order_by(AnomalyResult.detected_at.desc()).limit(limit).all()
    return [
        {
            "id": anomaly.id,
            "time": log.time,
            "src_ip": str(log.src_ip) if log.src_ip is not None else None,
            "dst_ip": str(log.dst_ip) if log.dst_ip is not None else None,
            "protocol": log.protocol,
            "dst_port": log.dst_port,
            "anomaly_score": anomaly.anomaly_score,
            "severity": anomaly.severity,
            "confidence": anomaly.confidence,
            "algorithm": anomaly.algorithm,
            "has_ai_analysis": llm is not None,
        }
        for anomaly, log, llm in rows
    ]


def get_anomaly_trends(db: Session, days: int = 14, upload_ids: list[int] | None = None) -> list[dict]:
    # Grouping granularity is decided from the actual span of the (already
    # upload-scoped) data, not a fixed "always by day" bucket. If everything
    # in scope falls on the same calendar day (typical for a single upload),
    # grouping by day collapses everything into one flat point even though
    # the underlying logs have different hours. Falling back to hourly
    # buckets in that case gives a real, changing time-series line instead
    # of a single dot — without ever inventing data.
    span_q = _apply_upload_filter(
        db.query(func.min(FirewallLog.time), func.max(FirewallLog.time))
        .join(AnomalyResult, AnomalyResult.firewall_log_id == FirewallLog.id),
        upload_ids,
    )
    span = span_q.one()
    min_time, max_time = span
    if min_time is None or max_time is None:
        return []

    span_hours = (max_time - min_time).total_seconds() / 3600
    use_hourly = span_hours <= 36  # a day and a half or less of real data -> hourly buckets

    bucket_expr = func.date_trunc("hour" if use_hourly else "day", FirewallLog.time)
    bucket_limit = 72 if use_hourly else days  # ~3 days of hourly buckets is a generous safety cap

    rows_q = _apply_upload_filter(
        db.query(
            bucket_expr.label("bucket"),
            func.sum(case((AnomalyResult.is_anomaly.is_(True), 1), else_=0)).label("anomalies"),
            func.sum(case((AnomalyResult.is_anomaly.is_(False), 1), else_=0)).label("normal"),
        )
        .join(AnomalyResult, AnomalyResult.firewall_log_id == FirewallLog.id),
        upload_ids,
    )
    rows = rows_q.group_by(bucket_expr).order_by(bucket_expr.desc()).limit(bucket_limit).all()

    label_fmt = "%b %d, %H:%M" if use_hourly else "%b %d, %Y"
    return [
        {
            "date": r.bucket.strftime(label_fmt),
            "anomalies": int(r.anomalies or 0),
            "normal": int(r.normal or 0),
        }
        for r in reversed(rows)
    ]


def get_top_ips(
    db: Session, column: str = "src_ip", limit: int = 10, upload_ids: list[int] | None = None,
) -> list[dict]:
    ip_col = FirewallLog.src_ip if column == "src_ip" else FirewallLog.dst_ip
    query = (
        db.query(ip_col.label("ip"), func.count(AnomalyResult.id).label("cnt"))
        .join(AnomalyResult, AnomalyResult.firewall_log_id == FirewallLog.id)
        .filter(AnomalyResult.is_anomaly.is_(True), ip_col.is_not(None))
    )
    query = _apply_upload_filter(query, upload_ids)
    rows = query.group_by(ip_col).order_by(func.count(AnomalyResult.id).desc()).limit(limit).all()
    return [{"ip": str(r.ip), "anomaly_count": r.cnt} for r in rows]


def get_protocol_distribution(db: Session, upload_ids: list[int] | None = None) -> list[dict]:
    query = db.query(FirewallLog.protocol, func.count(FirewallLog.id).label("cnt")).filter(
        FirewallLog.protocol.is_not(None)
    )
    query = _apply_upload_filter(query, upload_ids)
    rows = query.group_by(FirewallLog.protocol).order_by(func.count(FirewallLog.id).desc()).all()
    return [{"label": r.protocol, "count": r.cnt} for r in rows]


def get_rule_type_distribution(db: Session, upload_ids: list[int] | None = None) -> list[dict]:
    query = db.query(FirewallLog.rule_type, func.count(FirewallLog.id).label("cnt")).filter(
        FirewallLog.rule_type.is_not(None)
    )
    query = _apply_upload_filter(query, upload_ids)
    rows = query.group_by(FirewallLog.rule_type).order_by(func.count(FirewallLog.id).desc()).all()
    return [{"label": r.rule_type or "Unknown", "count": r.cnt} for r in rows]


def get_top_destination_ports(db: Session, limit: int = 10, upload_ids: list[int] | None = None) -> list[dict]:
    query = db.query(FirewallLog.dst_port, func.count(FirewallLog.id).label("cnt")).filter(
        FirewallLog.dst_port.is_not(None)
    )
    query = _apply_upload_filter(query, upload_ids)
    rows = query.group_by(FirewallLog.dst_port).order_by(func.count(FirewallLog.id).desc()).limit(limit).all()
    return [{"label": str(r.dst_port), "count": r.cnt} for r in rows]


def get_firewall_rule_activity(db: Session, limit: int = 10, upload_ids: list[int] | None = None) -> list[dict]:
    name_col = func.coalesce(FirewallLog.firewall_rule_name, FirewallLog.firewall_rule)
    query = db.query(name_col.label("rule"), func.count(FirewallLog.id).label("cnt")).filter(
        name_col.is_not(None)
    )
    query = _apply_upload_filter(query, upload_ids)
    rows = query.group_by(name_col).order_by(func.count(FirewallLog.id).desc()).limit(limit).all()
    return [{"label": r.rule, "count": r.cnt} for r in rows]
