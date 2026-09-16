from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class AssistantChatResponse(BaseModel):
    reply: str


class ReportGenerateRequest(BaseModel):
    period: Literal["today", "weekly", "monthly", "all"] = "today"
    report_type: Literal["executive_summary", "incident_report", "threat_overview"] = "executive_summary"


class ReportGenerateResponse(BaseModel):
    allowed: bool = True
    message: Optional[str] = None
    report_type: str
    period: str
    generated_at: datetime
    report_text: Optional[str] = None
    stats_used: Optional[dict] = None
