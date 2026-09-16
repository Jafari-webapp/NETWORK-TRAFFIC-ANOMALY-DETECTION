"""
CRUD + bulk upload for firewall_logs. Handles CSV/XLSX validation, column
normalization, and inserting only valid rows — invalid rows are reported back,
never silently dropped (spec section 40).
"""
import io
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.models.firewall_log import FirewallLog
from app.models.upload_history import UploadHistory
from app.schemas.firewall_log import FirewallLogCreate

logger = logging.getLogger("app.services.firewall")

REQUIRED_COLUMNS = [
    "Time", "Log comp", "Log subtype", "Username", "Firewall rule",
    "Firewall rule name", "NAT rule", "NAT rule name", "In interface",
    "Out interface", "Src IP", "Dst IP", "Src port", "Dst port", "Protocol",
    "Rule type", "Live PCAP", "Message", "Log occurrence",
]

# snake_case -> Title Case, so files exported straight from the DB/API also work
_COLUMN_ALIASES = {
    "time": "Time", "log_comp": "Log comp", "log_subtype": "Log subtype",
    "username": "Username", "firewall_rule": "Firewall rule",
    "firewall_rule_name": "Firewall rule name", "nat_rule": "NAT rule",
    "nat_rule_name": "NAT rule name", "in_interface": "In interface",
    "out_interface": "Out interface", "src_ip": "Src IP", "dst_ip": "Dst IP",
    "src_port": "Src port", "dst_port": "Dst port", "protocol": "Protocol",
    "rule_type": "Rule type", "live_pcap": "Live PCAP", "message": "Message",
    "log_occurrence": "Log occurrence",
}


def create_log(db: Session, data: FirewallLogCreate) -> FirewallLog:
    log = FirewallLog(**data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_log(db: Session, log_id: int) -> FirewallLog | None:
    return db.get(FirewallLog, log_id)


def delete_log(db: Session, log_id: int) -> bool:
    log = db.get(FirewallLog, log_id)
    if not log:
        return False
    db.delete(log)
    db.commit()
    return True


def list_logs(
    db: Session, page: int = 1, page_size: int = 20,
    protocol: str | None = None, src_ip: str | None = None, dst_ip: str | None = None,
    date_from: datetime | None = None, date_to: datetime | None = None,
    sort_by: str = "time", sort_dir: str = "desc",
):
    query = select(FirewallLog)
    count_query = select(func.count()).select_from(FirewallLog)

    # Protocol: exact but case-insensitive (values are short codes like TCP/UDP/ICMP).
    if protocol:
        proto_match = func.lower(FirewallLog.protocol) == protocol.lower()
        query = query.where(proto_match)
        count_query = count_query.where(proto_match)
    # src_ip/dst_ip are Postgres INET columns, so comparing them directly to a
    # partial string like "192.168" raises "invalid input syntax for type inet"
    # (a 500, not an empty result). Cast to text first so partial/substring
    # search works the way a Network Engineer expects from a search box.
    if src_ip:
        src_match = cast(FirewallLog.src_ip, String).ilike(f"%{src_ip}%")
        query = query.where(src_match)
        count_query = count_query.where(src_match)
    if dst_ip:
        dst_match = cast(FirewallLog.dst_ip, String).ilike(f"%{dst_ip}%")
        query = query.where(dst_match)
        count_query = count_query.where(dst_match)
    if date_from:
        query = query.where(FirewallLog.time >= date_from)
        count_query = count_query.where(FirewallLog.time >= date_from)
    if date_to:
        query = query.where(FirewallLog.time <= date_to)
        count_query = count_query.where(FirewallLog.time <= date_to)

    sort_col = getattr(FirewallLog, sort_by, FirewallLog.time)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    total = db.execute(count_query).scalar_one()
    items = db.execute(query).scalars().all()
    return items, total


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {c: _COLUMN_ALIASES.get(c.strip().lower(), c.strip()) for c in df.columns}
    return df.rename(columns=rename_map)


def _row_to_clean_dict(row: pd.Series) -> tuple[dict | None, str | None]:
    try:
        time_val = pd.to_datetime(row.get("Time"), errors="coerce")
        if pd.isna(time_val):
            return None, "Invalid or missing Time value"

        def _clean_ip(v):
            v = str(v).strip() if pd.notna(v) else None
            return v if v and v.lower() not in ("nan", "unknown", "") else None

        def _clean_port(v):
            if pd.isna(v):
                return None
            try:
                p = int(float(v))
                return p if 0 <= p <= 65535 else None
            except (ValueError, TypeError):
                return None

        def _clean_str(v):
            if pd.isna(v):
                return None
            s = str(v).strip()
            return s if s and s.lower() != "nan" else None

        return {
            "time": time_val.to_pydatetime().replace(tzinfo=timezone.utc),
            "log_comp": _clean_str(row.get("Log comp")),
            "log_subtype": _clean_str(row.get("Log subtype")),
            "username": _clean_str(row.get("Username")),
            "firewall_rule": _clean_str(row.get("Firewall rule")),
            "firewall_rule_name": _clean_str(row.get("Firewall rule name")),
            "nat_rule": _clean_str(row.get("NAT rule")),
            "nat_rule_name": _clean_str(row.get("NAT rule name")),
            "in_interface": _clean_str(row.get("In interface")),
            "out_interface": _clean_str(row.get("Out interface")),
            "src_ip": _clean_ip(row.get("Src IP")),
            "dst_ip": _clean_ip(row.get("Dst IP")),
            "src_port": _clean_port(row.get("Src port")),
            "dst_port": _clean_port(row.get("Dst port")),
            "protocol": _clean_str(row.get("Protocol")),
            "rule_type": _clean_str(row.get("Rule type")),
            "live_pcap": _clean_str(row.get("Live PCAP")),
            "message": _clean_str(row.get("Message")),
            "log_occurrence": _clean_port(row.get("Log occurrence")) or 0,
        }, None
    except Exception as exc:
        return None, str(exc)


def parse_upload_file(filename: str, content: bytes) -> pd.DataFrame:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "csv":
        df = pd.read_csv(io.BytesIO(content))
    elif ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise ValueError("Unsupported file type. Allowed: .csv, .xlsx, .xls")
    return _normalize_columns(df)


def validate_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


# If most required network/firewall columns are absent, this almost certainly isn't
# a Sophos/network log export at all (e.g. someone uploaded a customer or sales
# spreadsheet) — worth a clearer message than just "missing columns: <18 names>".
def looks_like_unrelated_dataset(missing: list[str]) -> bool:
    return len(missing) >= len(REQUIRED_COLUMNS) * 0.7


MAX_UPLOAD_HISTORY = 10


def list_upload_history(db: Session) -> list[UploadHistory]:
    stmt = select(UploadHistory).order_by(UploadHistory.uploaded_at.desc()).limit(MAX_UPLOAD_HISTORY)
    return list(db.execute(stmt).scalars().all())


def count_upload_history(db: Session) -> int:
    return db.execute(select(func.count(UploadHistory.id))).scalar() or 0


def delete_upload_history_entry(db: Session, entry_id: int) -> bool:
    record = db.get(UploadHistory, entry_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def clear_upload_history(db: Session) -> int:
    records = list(db.execute(select(UploadHistory)).scalars().all())
    count = len(records)
    for r in records:
        db.delete(r)
    db.commit()
    return count


def bulk_insert_from_dataframe(
    db: Session, df: pd.DataFrame, upload_history_id: int | None = None,
) -> tuple[list[FirewallLog], int, list[dict]]:
    """Returns (inserted_orm_objects, invalid_row_count, rejected_row_errors[:50])."""
    valid_rows: list[dict] = []
    errors: list[dict] = []

    for idx, row in df.iterrows():
        clean, err = _row_to_clean_dict(row)
        if clean is None:
            errors.append({"row": int(idx) + 1, "error": err})
        else:
            valid_rows.append(clean)

    inserted: list[FirewallLog] = []
    if valid_rows:
        objs = [FirewallLog(upload_history_id=upload_history_id, **r) for r in valid_rows]
        db.add_all(objs)
        db.commit()
        for o in objs:
            db.refresh(o)
        inserted = objs

    return inserted, len(errors), errors[:50]


def record_upload_history(
    db: Session, filename: str, total_rows: int, valid_rows: int,
    invalid_rows: int, inserted_rows: int, status: str,
) -> UploadHistory:
    record = UploadHistory(
        filename=filename, total_rows=total_rows, valid_rows=valid_rows,
        invalid_rows=invalid_rows, inserted_rows=inserted_rows, status=status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_pending_upload_history(db: Session, filename: str) -> UploadHistory:
    """Create the history row up front so its id can be used to tag inserted
    FirewallLog rows with the upload batch they belong to (View/Combined/All
    Insights). Finalized afterwards with finalize_upload_history()."""
    record = UploadHistory(filename=filename, status="processing")
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def finalize_upload_history(
    db: Session, record: UploadHistory, total_rows: int, valid_rows: int,
    invalid_rows: int, inserted_rows: int, status: str,
) -> UploadHistory:
    record.total_rows = total_rows
    record.valid_rows = valid_rows
    record.invalid_rows = invalid_rows
    record.inserted_rows = inserted_rows
    record.status = status
    db.commit()
    db.refresh(record)
    return record
