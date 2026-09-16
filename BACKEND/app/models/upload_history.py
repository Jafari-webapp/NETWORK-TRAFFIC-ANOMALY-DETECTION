"""
Extra table not in your original list, needed to support Stage 40/50 (file upload +
upload history). Kept separate from model_runs because a single upload can be
rejected before any ML run happens (e.g. missing columns) — we still want to record
that attempt.
"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UploadHistory(Base):
    __tablename__ = "upload_history"
    __table_args__ = {"schema": "network"}

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
