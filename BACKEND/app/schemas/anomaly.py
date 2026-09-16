from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.firewall_log import FirewallLogResponse
from app.schemas.llm import LLMAnalysisResponse


class AnomalyResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    firewall_log_id: int
    is_anomaly: bool
    anomaly_score: float
    algorithm: str
    severity: Optional[str] = None
    confidence: Optional[float] = None
    detected_at: datetime


class AnomalyDetailResponse(AnomalyResultResponse):
    """Full detail view: network info + detection + AI analysis, matches spec section 48."""
    firewall_log: FirewallLogResponse
    llm_analysis: Optional[LLMAnalysisResponse] = None


class DetectRequest(BaseModel):
    firewall_log_id: int


class DetectAndAnalyzeResponse(BaseModel):
    anomaly: AnomalyResultResponse
    llm_analysis: Optional[LLMAnalysisResponse] = None
