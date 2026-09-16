from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.anomaly_result import AnomalyResult
from app.models.firewall_log import FirewallLog
from app.models.system_user import SystemUser
from app.schemas.anomaly import (
    AnomalyDetailResponse, AnomalyResultResponse, DetectAndAnalyzeResponse, DetectRequest,
)
from app.services import firewall_service
from app.services.anomaly_service import analyze_with_gemini, run_detection_for_log
from app.services.llm_service import GeminiUnavailableError

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


@router.post("/detect", response_model=AnomalyResultResponse)
def detect(payload: DetectRequest, db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user)):
    log = firewall_service.get_log(db, payload.firewall_log_id)
    if not log:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Firewall log not found")
    return run_detection_for_log(db, log)


@router.post("/detect-and-analyze", response_model=DetectAndAnalyzeResponse)
def detect_and_analyze(
    payload: DetectRequest, db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user),
):
    log = firewall_service.get_log(db, payload.firewall_log_id)
    if not log:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Firewall log not found")

    anomaly = run_detection_for_log(db, log)

    llm_result = None
    if anomaly.is_anomaly:
        try:
            llm_result = analyze_with_gemini(db, anomaly)
        except GeminiUnavailableError as exc:
            # Detection result is already saved; surface the Gemini failure without losing it.
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Anomaly saved, but Gemini analysis failed: {exc}")

    return DetectAndAnalyzeResponse(anomaly=anomaly, llm_analysis=llm_result)


@router.get("/{anomaly_id}", response_model=AnomalyDetailResponse)
def get_anomaly_detail(
    anomaly_id: int, db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user),
):
    anomaly = (
        db.query(AnomalyResult)
        .options(joinedload(AnomalyResult.firewall_log), joinedload(AnomalyResult.llm_analysis))
        .filter(AnomalyResult.id == anomaly_id)
        .one_or_none()
    )
    if not anomaly:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anomaly not found")
    return anomaly
