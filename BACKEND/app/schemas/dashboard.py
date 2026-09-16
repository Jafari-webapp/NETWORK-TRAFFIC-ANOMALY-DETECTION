from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_logs: int
    total_anomalies: int
    normal_logs: int
    low_severity: int
    medium_severity: int
    high_severity: int
    critical_severity: int
    unique_src_ips: int
    unique_dst_ips: int
    anomaly_rate: float


class DistributionSlice(BaseModel):
    label: str
    count: int


class RecentAnomalyItem(BaseModel):
    id: int
    time: datetime
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    protocol: Optional[str] = None
    dst_port: Optional[int] = None
    anomaly_score: float
    severity: Optional[str] = None
    confidence: Optional[float] = None
    algorithm: str
    has_ai_analysis: bool


class AnomalyTrendPoint(BaseModel):
    date: str
    anomalies: int
    normal: int


class TopIP(BaseModel):
    ip: str
    anomaly_count: int
