import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.system_user import SystemUser
from app.schemas.firewall_log import (
    BulkUploadResult, FirewallLogCreate, FirewallLogResponse, PaginatedFirewallLogs,
    UploadHistoryResponse,
)
from app.services import firewall_service
from app.services.anomaly_service import run_detection_for_logs

router = APIRouter(prefix="/api/logs", tags=["firewall-logs"])


@router.post("", response_model=FirewallLogResponse, status_code=status.HTTP_201_CREATED)
def create_log(
    data: FirewallLogCreate, db: Session = Depends(get_db),
    _: SystemUser = Depends(get_current_user),
):
    return firewall_service.create_log(db, data)


@router.get("", response_model=PaginatedFirewallLogs)
def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    protocol: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: SystemUser = Depends(get_current_user),
):
    items, total = firewall_service.list_logs(
        db, page=page, page_size=page_size, protocol=protocol,
        src_ip=src_ip, dst_ip=dst_ip, date_from=date_from, date_to=date_to,
    )
    return PaginatedFirewallLogs(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=max(math.ceil(total / page_size), 1),
    )


@router.get("/search", response_model=PaginatedFirewallLogs)
def search_logs(
    protocol: str | None = None, src_ip: str | None = None, dst_ip: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user),
):
    return list_logs(page, page_size, protocol, src_ip, dst_ip, None, None, db, _)


@router.get("/upload-history", response_model=list[UploadHistoryResponse])
def get_upload_history(db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user)):
    return firewall_service.list_upload_history(db)


@router.delete("/upload-history", status_code=status.HTTP_200_OK)
def clear_upload_history(db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user)):
    deleted = firewall_service.clear_upload_history(db)
    return {"deleted": deleted}


@router.delete("/upload-history/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload_history_entry(
    entry_id: int, db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user),
):
    if not firewall_service.delete_upload_history_entry(db, entry_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Upload history entry not found")


@router.get("/{log_id}", response_model=FirewallLogResponse)
def get_log(log_id: int, db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user)):
    log = firewall_service.get_log(db, log_id)
    if not log:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Firewall log not found")
    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(log_id: int, db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user)):
    if not firewall_service.delete_log(db, log_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Firewall log not found")


@router.post("/bulk", response_model=BulkUploadResult, status_code=status.HTTP_201_CREATED)
def bulk_create(
    rows: list[FirewallLogCreate], db: Session = Depends(get_db),
    _: SystemUser = Depends(get_current_user),
):
    import pandas as pd
    df = pd.DataFrame([r.model_dump() for r in rows])
    # Reuse the same validated insert path as file upload for consistency.
    title_map = {
        "time": "Time", "log_comp": "Log comp", "log_subtype": "Log subtype",
        "username": "Username", "firewall_rule": "Firewall rule",
        "firewall_rule_name": "Firewall rule name", "nat_rule": "NAT rule",
        "nat_rule_name": "NAT rule name", "in_interface": "In interface",
        "out_interface": "Out interface", "src_ip": "Src IP", "dst_ip": "Dst IP",
        "src_port": "Src port", "dst_port": "Dst port", "protocol": "Protocol",
        "rule_type": "Rule type", "live_pcap": "Live PCAP", "message": "Message",
        "log_occurrence": "Log occurrence",
    }
    df = df.rename(columns=title_map)
    inserted, invalid_count, errors = firewall_service.bulk_insert_from_dataframe(db, df)
    return BulkUploadResult(
        filename="bulk-request", total_rows=len(rows), valid_rows=len(inserted),
        invalid_rows=invalid_count, inserted_rows=len(inserted),
        status="success" if inserted else "error", rejected_row_errors=errors,
    )


@router.post("/upload", response_model=BulkUploadResult, status_code=status.HTTP_201_CREATED)
def upload_logs(
    file: UploadFile, db: Session = Depends(get_db),
    _: SystemUser = Depends(get_current_user),
):
    if not file.filename or "." not in file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must have a valid extension")
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .csv, .xlsx, .xls files are accepted")

    # Upload History is retained on a 1-month time basis only (see cleanup_service) —
    # it is never capped by record count, so no upload is ever blocked here.
    upload_record = firewall_service.create_pending_upload_history(db, file.filename)

    content = file.file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        firewall_service.finalize_upload_history(db, upload_record, 0, 0, 0, 0, "error")
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )

    try:
        df = firewall_service.parse_upload_file(file.filename, content)
    except Exception as exc:
        firewall_service.finalize_upload_history(db, upload_record, 0, 0, 0, 0, "error")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not read file: {exc}")

    missing = firewall_service.validate_columns(df)
    if missing:
        friendly = (
            "Invalid dataset. This file does not appear to contain supported "
            "network/firewall log data. Please upload a valid Sophos Firewall "
            "or network traffic log dataset."
            if firewall_service.looks_like_unrelated_dataset(missing)
            else "Some required network log columns are missing from this file."
        )
        result = BulkUploadResult(
            filename=file.filename, upload_history_id=upload_record.id,
            total_rows=len(df), valid_rows=0,
            invalid_rows=len(df), inserted_rows=0, status="error",
            message=friendly, missing_columns=missing,
        )
        firewall_service.finalize_upload_history(
            db, upload_record, len(df), 0, len(df), 0, "error",
        )
        return result

    inserted, invalid_count, errors = firewall_service.bulk_insert_from_dataframe(
        db, df, upload_history_id=upload_record.id,
    )

    # Run detection + Gemini (for anomalies only) right after a successful upload.
    if inserted:
        anomalies = run_detection_for_logs(db, inserted)
        from app.services.anomaly_service import analyze_with_gemini
        from app.services.llm_service import GeminiUnavailableError
        for a in anomalies:
            if a.is_anomaly:
                try:
                    analyze_with_gemini(db, a)
                except GeminiUnavailableError:
                    # Don't fail the whole upload if Gemini/API key isn't configured yet —
                    # detection results are already saved; AI analysis can be retried later.
                    pass

    status_label = "success" if not errors else ("partial" if inserted else "error")
    firewall_service.finalize_upload_history(
        db, upload_record, len(df), len(inserted), invalid_count, len(inserted), status_label,
    )
    return BulkUploadResult(
        filename=file.filename, upload_history_id=upload_record.id,
        total_rows=len(df), valid_rows=len(inserted),
        invalid_rows=invalid_count, inserted_rows=len(inserted),
        status=status_label, rejected_row_errors=errors,
    )

