from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class GeminiStructuredOutput(BaseModel):
    """The exact JSON shape we require back from Gemini (spec section 19)."""
    analysis: str
    possible_cause: str
    recommendation: str
    risk_explanation: str


class LLMAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    anomaly_id: int
    model_name: str
    provider: str
    analysis: Optional[str] = None
    possible_cause: Optional[str] = None
    recommendation: Optional[str] = None
    risk_explanation: Optional[str] = None
    generated_at: datetime
