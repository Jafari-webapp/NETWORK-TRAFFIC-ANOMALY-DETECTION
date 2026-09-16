from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SystemUser(Base):
    __tablename__ = "system_users"
    __table_args__ = {"schema": "network"}

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(150))
    organization: Mapped[str | None] = mapped_column(String(150))
    # Single-user system today (one Network Engineer) but kept as a field so
    # more roles can be added later without a schema change.
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="network_engineer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Settings / preferences (Profile > Settings page) ---
    # Notification toggles are stored for real, but no email/SMS/push channel
    # is wired up yet — they don't currently trigger anything. Left honest
    # about that in the UI rather than pretending alerts go out.
    notify_anomaly_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_system: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Dar_es_Salaam")
    dashboard_default_range_days: Mapped[int] = mapped_column(Integer, default=14)
    dashboard_refresh_interval_seconds: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
