from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FirewallLogBase(BaseModel):
    time: datetime
    log_comp: Optional[str] = None
    log_subtype: Optional[str] = None
    username: Optional[str] = None
    firewall_rule: Optional[str] = None
    firewall_rule_name: Optional[str] = None
    nat_rule: Optional[str] = None
    nat_rule_name: Optional[str] = None
    in_interface: Optional[str] = None
    out_interface: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = Field(default=None, ge=0, le=65535)
    dst_port: Optional[int] = Field(default=None, ge=0, le=65535)
    protocol: Optional[str] = None
    rule_type: Optional[str] = None
    live_pcap: Optional[str] = None
    message: Optional[str] = None
    log_occurrence: Optional[int] = None

    @field_validator("src_ip", "dst_ip", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        # psycopg returns Postgres INET columns as ipaddress.IPv4Address/
        # IPv6Address objects, not str — convert before Pydantic's strict
        # string validation runs, or any row with a real IP fails to serialize.
        if v is None:
            return None
        v = str(v)
        return None if v.strip() == "" else v


class FirewallLogCreate(FirewallLogBase):
    pass


class FirewallLogUpdate(BaseModel):
    """All fields optional — partial update."""
    log_comp: Optional[str] = None
    log_subtype: Optional[str] = None
    username: Optional[str] = None
    firewall_rule: Optional[str] = None
    firewall_rule_name: Optional[str] = None
    nat_rule: Optional[str] = None
    nat_rule_name: Optional[str] = None
    in_interface: Optional[str] = None
    out_interface: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = Field(default=None, ge=0, le=65535)
    dst_port: Optional[int] = Field(default=None, ge=0, le=65535)
    protocol: Optional[str] = None
    rule_type: Optional[str] = None
    live_pcap: Optional[str] = None
    message: Optional[str] = None
    log_occurrence: Optional[int] = None


class FirewallLogResponse(FirewallLogBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class PaginatedFirewallLogs(BaseModel):
    items: list[FirewallLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkUploadResult(BaseModel):
    filename: str
    upload_history_id: Optional[int] = None
    total_rows: int
    valid_rows: int
    invalid_rows: int
    inserted_rows: int
    status: str
    message: Optional[str] = None
    missing_columns: list[str] = []
    rejected_row_errors: list[dict] = []


class UploadHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    inserted_rows: int
    status: str
    uploaded_at: datetime
