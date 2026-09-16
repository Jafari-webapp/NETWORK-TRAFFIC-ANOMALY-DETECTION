from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class LLMAnalysis(Base):
    __tablename__ = "llm_analysis"
    __table_args__ = {"schema": "network"}

    id: Mapped[int] = mapped_column(primary_key=True)
    anomaly_id: Mapped[int] = mapped_column(
        ForeignKey("network.anomaly_results.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="Google Gemini")
    analysis: Mapped[str | None] = mapped_column(Text)
    possible_cause: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    risk_explanation: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    anomaly = relationship("AnomalyResult", back_populates="llm_analysis")
