from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Text, func, Index, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class FirewallLog(Base):
    __tablename__ = "firewall_logs"
    __table_args__ = (
        Index("ix_firewall_logs_time", "time"),
        Index("ix_firewall_logs_src_ip", "src_ip"),
        Index("ix_firewall_logs_dst_ip", "dst_ip"),
        Index("ix_firewall_logs_upload_history_id", "upload_history_id"),
        CheckConstraint("src_port IS NULL OR (src_port BETWEEN 0 AND 65535)", name="ck_firewall_logs_src_port"),
        CheckConstraint("dst_port IS NULL OR (dst_port BETWEEN 0 AND 65535)", name="ck_firewall_logs_dst_port"),
        {"schema": "network"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    log_comp: Mapped[str | None] = mapped_column(String(100))
    log_subtype: Mapped[str | None] = mapped_column(String(100))
    username: Mapped[str | None] = mapped_column(String(150))
    firewall_rule: Mapped[str | None] = mapped_column(String(50))
    firewall_rule_name: Mapped[str | None] = mapped_column(String(255))
    nat_rule: Mapped[str | None] = mapped_column(String(50))
    nat_rule_name: Mapped[str | None] = mapped_column(String(255))
    in_interface: Mapped[str | None] = mapped_column(String(50))
    out_interface: Mapped[str | None] = mapped_column(String(50))
    # Nullable: Sophos "Could not associate packet to any connection" rows have no IP recorded.
    src_ip: Mapped[str | None] = mapped_column(INET)
    dst_ip: Mapped[str | None] = mapped_column(INET)
    src_port: Mapped[int | None] = mapped_column(Integer)
    dst_port: Mapped[int | None] = mapped_column(Integer)
    protocol: Mapped[str | None] = mapped_column(String(20))
    rule_type: Mapped[str | None] = mapped_column(String(20))
    live_pcap: Mapped[str | None] = mapped_column(String(50))
    message: Mapped[str | None] = mapped_column(Text)
    log_occurrence: Mapped[int | None] = mapped_column(Integer)
    # Which upload batch this row came from. Nullable so old rows inserted before
    # this column existed (or via the manual /api/logs POST/bulk endpoints) keep working.
    upload_history_id: Mapped[int | None] = mapped_column(
        ForeignKey("network.upload_history.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    anomaly_result: Mapped["AnomalyResult | None"] = relationship(
        back_populates="firewall_log", uselist=False, cascade="all, delete-orphan"
    )