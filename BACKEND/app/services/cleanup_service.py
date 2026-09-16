"""
Automatic data retention.

- Firewall Logs + Anomaly Results (and their cascaded LLM analyses): deleted
  once older than FIREWALL_LOG_RETENTION_DAYS (1 calendar month).
- Upload History: deleted once older than UPLOAD_HISTORY_RETENTION_DAYS
  (1 calendar month) — time-based only, never limited by record count.

Runs periodically from a background asyncio task started in main.py's
startup event — no user action (opening the Dashboard/Upload History page)
is required for cleanup to happen.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal, engine
from app.models.firewall_log import FirewallLog
from app.models.upload_history import UploadHistory

logger = logging.getLogger("app.services.cleanup")

FIREWALL_LOG_RETENTION_DAYS = 30
UPLOAD_HISTORY_RETENTION_DAYS = 30

CLEANUP_INTERVAL_SECONDS = 60 * 60  # run once an hour


def ensure_schema_upgrades() -> None:
    """
    Idempotent, additive-only schema upgrade for existing databases created
    before the upload_history_id column existed. Safe to run every startup —
    does nothing if the column/index already exist, and never touches or
    deletes any existing data.
    """
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE network.firewall_logs "
            "ADD COLUMN IF NOT EXISTS upload_history_id INTEGER "
            "REFERENCES network.upload_history(id) ON DELETE SET NULL"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_firewall_logs_upload_history_id "
            "ON network.firewall_logs (upload_history_id)"
        ))
    logger.info("Schema check complete (upload_history_id column present).")


def run_retention_cleanup(db: Session) -> dict:
    """Delete expired Firewall Logs/Anomalies and Upload History rows. Returns counts."""
    now = datetime.now(timezone.utc)

    log_cutoff = now - timedelta(days=FIREWALL_LOG_RETENTION_DAYS)
    # AnomalyResult and LLMAnalysis rows are removed automatically via
    # ON DELETE CASCADE foreign keys — deleting the FirewallLog row is enough.
    deleted_logs = (
        db.query(FirewallLog)
        .filter(FirewallLog.time < log_cutoff)
        .delete(synchronize_session=False)
    )

    history_cutoff = now - timedelta(days=UPLOAD_HISTORY_RETENTION_DAYS)
    deleted_history = (
        db.query(UploadHistory)
        .filter(UploadHistory.uploaded_at < history_cutoff)
        .delete(synchronize_session=False)
    )

    db.commit()

    if deleted_logs or deleted_history:
        logger.info(
            "Retention cleanup: removed %d firewall log(s) older than %dd, "
            "%d upload history record(s) older than %dd.",
            deleted_logs, FIREWALL_LOG_RETENTION_DAYS, deleted_history, UPLOAD_HISTORY_RETENTION_DAYS,
        )

    return {"deleted_logs": deleted_logs, "deleted_upload_history": deleted_history}


async def cleanup_loop() -> None:
    """Background task: run retention cleanup once at startup, then hourly forever."""
    import asyncio

    while True:
        try:
            db = SessionLocal()
            try:
                run_retention_cleanup(db)
            finally:
                db.close()
        except Exception:
            logger.exception("Retention cleanup run failed — will retry on the next interval.")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
