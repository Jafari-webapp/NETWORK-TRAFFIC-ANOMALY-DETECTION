from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ModelRun(Base):
    __tablename__ = "model_runs"
    __table_args__ = {"schema": "network"}

    id: Mapped[int] = mapped_column(primary_key=True)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50))
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    anomalies_detected: Mapped[int] = mapped_column(Integer, default=0)
    normal_records: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")  # RUNNING, SUCCESS, FAILED
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
