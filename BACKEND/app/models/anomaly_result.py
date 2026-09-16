from datetime import datetime

from sqlalchemy import Boolean, Float, String, DateTime, ForeignKey, func, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AnomalyResult(Base):
    __tablename__ = "anomaly_results"
    __table_args__ = (
        Index("ix_anomaly_results_is_anomaly", "is_anomaly"),
        Index("ix_anomaly_results_severity", "severity"),
        CheckConstraint(
            "severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="ck_anomaly_results_severity"
        ),
        {"schema": "network"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    firewall_log_id: Mapped[int] = mapped_column(
        ForeignKey("network.firewall_logs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default="IsolationForest+LOF")
    severity: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    firewall_log = relationship("FirewallLog", back_populates="anomaly_result")
    llm_analysis: Mapped["LLMAnalysis | None"] = relationship(
        back_populates="anomaly", uselist=False, cascade="all, delete-orphan"
    )