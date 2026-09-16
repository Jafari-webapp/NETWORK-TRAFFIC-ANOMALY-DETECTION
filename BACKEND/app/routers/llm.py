from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.anomaly_result import AnomalyResult
from app.models.llm_analysis import LLMAnalysis
from app.models.system_user import SystemUser
from app.schemas.llm import LLMAnalysisResponse
from app.services.anomaly_service import analyze_with_gemini
from app.services.llm_service import GeminiUnavailableError

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.post("/analyze/{anomaly_id}", response_model=LLMAnalysisResponse)
def analyze(anomaly_id: int, db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user)):
    anomaly = db.get(AnomalyResult, anomaly_id)
    if not anomaly:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anomaly not found")
    if not anomaly.is_anomaly:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Gemini is only used for confirmed anomalies")

    try:
        result = analyze_with_gemini(db, anomaly)
    except GeminiUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return result


@router.get("/analyze/{anomaly_id}", response_model=LLMAnalysisResponse)
def get_analysis(anomaly_id: int, db: Session = Depends(get_db), _: SystemUser = Depends(get_current_user)):
    record = db.query(LLMAnalysis).filter_by(anomaly_id=anomaly_id).one_or_none()
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No AI analysis found for this anomaly yet")
    return record
