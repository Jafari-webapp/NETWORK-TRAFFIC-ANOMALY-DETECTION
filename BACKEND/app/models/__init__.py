"""
Import every model here so Base.metadata.create_all() (and Alembic, later) sees them.
"""
from app.models.firewall_log import FirewallLog
from app.models.anomaly_result import AnomalyResult
from app.models.llm_analysis import LLMAnalysis
from app.models.model_run import ModelRun
from app.models.system_user import SystemUser
from app.models.audit_log import AuditLog
from app.models.upload_history import UploadHistory

__all__ = [
    "FirewallLog",
    "AnomalyResult",
    "LLMAnalysis",
    "ModelRun",
    "SystemUser",
    "AuditLog",
    "UploadHistory",
]
