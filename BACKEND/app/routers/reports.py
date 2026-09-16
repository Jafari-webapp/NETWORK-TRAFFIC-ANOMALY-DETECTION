from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.system_user import SystemUser
from app.schemas.assistant import ReportGenerateRequest, ReportGenerateResponse
from app.services import report_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/generate", response_model=ReportGenerateResponse)
def generate(
    payload: ReportGenerateRequest, db: Session = Depends(get_db),
    _: SystemUser = Depends(get_current_user),
):
    allowed, message, report_text, stats = report_service.generate_report(
        db, payload.period, payload.report_type,
    )
    return ReportGenerateResponse(
        allowed=allowed, message=message,
        report_type=payload.report_type, period=payload.period,
        generated_at=datetime.now(timezone.utc), report_text=report_text, stats_used=stats,
    )
