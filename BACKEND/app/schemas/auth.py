from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    full_name: str | None = None
    username: str


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str | None = None
    email: str | None = None
    department: str | None = None
    organization: str | None = None
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    timezone: str
    notify_anomaly_alerts: bool
    notify_system: bool
    dashboard_default_range_days: int
    dashboard_refresh_interval_seconds: int


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    department: str | None = None
    organization: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class PreferencesUpdateRequest(BaseModel):
    timezone: str | None = None
    notify_anomaly_alerts: bool | None = None
    notify_system: bool | None = None
    dashboard_default_range_days: int | None = Field(default=None, ge=1, le=90)
    dashboard_refresh_interval_seconds: int | None = Field(default=None, ge=0, le=3600)
