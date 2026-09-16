from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.anomaly_result import AnomalyResult
from app.models.firewall_log import FirewallLog
from app.services import dashboard_service

_PERIOD_LABELS = {"today": "Today", "weekly": "This Week", "monthly": "This Month", "all": "All Time"}

_REPORT_TITLES = {
    "executive_summary": "Executive Summary",
    "incident_report": "Incident Report",
    "threat_overview": "Threat Overview",
}


def _day_bounds(dt: datetime) -> tuple[datetime, datetime]:
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return start, end


def _week_bounds(dt: datetime) -> tuple[datetime, datetime]:
    monday = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday_end = monday + timedelta(days=7) - timedelta(microseconds=1)
    return monday, sunday_end


def _month_bounds(dt: datetime) -> tuple[datetime, datetime]:
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    end = next_month - timedelta(microseconds=1)
    return start, end


def _data_exists_in_range(db: Session, start: datetime, end: datetime, column=FirewallLog.time) -> bool:
    return (
        db.query(FirewallLog.id)
        .filter(column >= start, column <= end)
        .limit(1)
        .first()
        is not None
    )


def validate_period(db: Session, period: str) -> tuple[bool, str | None, datetime | None, datetime | None]:
    """
    Returns (allowed, rejection_message, range_start, range_end).
    range_start/end are None only for "all".
    """
    now = datetime.now(timezone.utc)

    if period == "today":
        # "Today" = data uploaded/processed within the last 24 hours (by DB insertion
        # time), not by the log's own event timestamp — a CSV uploaded today can
        # legitimately contain older historical traffic timestamps, and that upload
        # should still count as "today's data".
        start, end = now - timedelta(hours=24), now
        if not _data_exists_in_range(db, start, end, column=FirewallLog.created_at):
            return False, (
                "Today's report cannot be generated because no data has been uploaded "
                "for today. Please upload today's data first."
            ), start, end
        return True, None, start, end

    if period == "weekly":
        start, end = _week_bounds(now)
        if now < end:
            return False, (
                "Weekly report cannot be generated yet because the current week has not "
                "ended. Please wait until the week is complete."
            ), start, end
        if not _data_exists_in_range(db, start, end):
            return False, (
                "Weekly report cannot be generated because no data was uploaded for this week."
            ), start, end
        return True, None, start, end

    if period == "monthly":
        start, end = _month_bounds(now)
        if now < end:
            return False, (
                "Monthly report cannot be generated yet because the current month has not "
                "ended. Please wait until the month is complete."
            ), start, end
        if not _data_exists_in_range(db, start, end):
            return False, (
                "Monthly report cannot be generated because no data was uploaded for this month."
            ), start, end
        return True, None, start, end

    # "all" — no weekly/monthly completion restriction; just needs *some* data to exist.
    any_data = db.query(FirewallLog.id).limit(1).first() is not None
    if not any_data:
        return False, "All report cannot be generated because there is no data available in the system.", None, None
    return True, None, None, None


def _gather_stats(
    db: Session, start: datetime | None, end: datetime | None, time_column=FirewallLog.time,
) -> dict:
    log_query = db.query(FirewallLog)
    anomaly_query = db.query(AnomalyResult).join(FirewallLog, AnomalyResult.firewall_log_id == FirewallLog.id)
    if start is not None:
        log_query = log_query.filter(time_column >= start, time_column <= end)
        anomaly_query = anomaly_query.filter(time_column >= start, time_column <= end)

    total_logs = log_query.count()
    anomalies = anomaly_query.filter(AnomalyResult.is_anomaly.is_(True)).all()

    severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for a in anomalies:
        if a.severity in severity_counts:
            severity_counts[a.severity] += 1

    top_rules_q = (
        db.query(FirewallLog.firewall_rule_name, func.count(AnomalyResult.id))
        .join(AnomalyResult, AnomalyResult.firewall_log_id == FirewallLog.id)
        .filter(AnomalyResult.is_anomaly.is_(True))
    )
    if start is not None:
        top_rules_q = top_rules_q.filter(time_column >= start, time_column <= end)
    top_rules = (
        top_rules_q.group_by(FirewallLog.firewall_rule_name)
        .order_by(func.count(AnomalyResult.id).desc())
        .limit(5)
        .all()
    )

    top_source_ips = dashboard_service.get_top_ips(db, column="src_ip", limit=5)
    top_dest_ips = dashboard_service.get_top_ips(db, column="dst_ip", limit=5)

    detail_rows = []
    severe = [a for a in anomalies if a.severity in ("HIGH", "CRITICAL")][:15]
    for a in severe:
        log = a.firewall_log
        detail_rows.append(
            f"{log.time} | {log.src_ip}->{log.dst_ip}:{log.dst_port} ({log.protocol}) "
            f"| rule={log.firewall_rule_name} | severity={a.severity} | score={a.anomaly_score:.4f}"
        )

    return {
        "total_logs": total_logs,
        "total_anomalies": len(anomalies),
        "severity_counts": severity_counts,
        "top_rules": [{"rule": r or "unknown", "count": c} for r, c in top_rules],
        "top_source_ips": top_source_ips,
        "top_destination_ips": top_dest_ips,
        "severe_anomaly_samples": detail_rows,
    }


def _format_report_text(period: str, report_type: str, stats: dict) -> str:
    """
    Build a plain, deterministic report straight from the already-computed
    PostgreSQL stats — no AI/Gemini call, no invented text. Every number
    below is exactly what is in `stats`.
    """
    anomaly_rate = (
        round((stats["total_anomalies"] / stats["total_logs"]) * 100, 2)
        if stats["total_logs"] else 0.0
    )
    sev = stats["severity_counts"]

    lines: list[str] = []
    lines.append(f"# {_REPORT_TITLES.get(report_type, 'Standard Report')} — {_PERIOD_LABELS.get(period, period)}")
    lines.append("")
    lines.append("## Overview")
    lines.append(f"- Total traffic logs: {stats['total_logs']}")
    lines.append(f"- Total anomalies detected: {stats['total_anomalies']}")
    lines.append(f"- Anomaly rate: {anomaly_rate}%")
    lines.append("")
    lines.append("## Severity Breakdown")
    lines.append(f"- Critical: {sev['CRITICAL']}")
    lines.append(f"- High: {sev['HIGH']}")
    lines.append(f"- Medium: {sev['MEDIUM']}")
    lines.append(f"- Low: {sev['LOW']}")
    lines.append("")

    lines.append("## Top Firewall Rules Triggering Anomalies")
    if stats["top_rules"]:
        for r in stats["top_rules"]:
            lines.append(f"- {r['rule']}: {r['count']} anomalies")
    else:
        lines.append("- No anomalies recorded in this period.")
    lines.append("")

    lines.append("## Top Source IPs by Anomaly Count")
    if stats["top_source_ips"]:
        for ip in stats["top_source_ips"]:
            lines.append(f"- {ip['ip']}: {ip['anomaly_count']} anomalies")
    else:
        lines.append("- No anomalies recorded in this period.")
    lines.append("")

    lines.append("## Top Destination IPs by Anomaly Count")
    if stats["top_destination_ips"]:
        for ip in stats["top_destination_ips"]:
            lines.append(f"- {ip['ip']}: {ip['anomaly_count']} anomalies")
    else:
        lines.append("- No anomalies recorded in this period.")
    lines.append("")

    lines.append("## High / Critical Anomaly Details")
    if stats["severe_anomaly_samples"]:
        for row in stats["severe_anomaly_samples"]:
            lines.append(f"- {row}")
    else:
        lines.append("- No HIGH or CRITICAL severity anomalies in this period.")

    return "\n".join(lines)


def generate_report(db: Session, period: str, report_type: str) -> tuple[bool, str | None, str | None, dict | None]:
    """
    Standard (non-AI) report: pulls real statistics from PostgreSQL and
    formats them into a readable report. No Gemini/LLM call anywhere here.

    Returns (allowed, rejection_message, report_text, stats_used).
    When allowed is False, report_text/stats_used are None — no empty or
    misleading report is ever generated.
    """
    allowed, message, start, end = validate_period(db, period)
    if not allowed:
        return False, message, None, None

    time_column = FirewallLog.created_at if period == "today" else FirewallLog.time
    stats = _gather_stats(db, start, end, time_column=time_column)
    report_text = _format_report_text(period, report_type, stats)
    return True, None, report_text, stats
