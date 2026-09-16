from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.system_user import SystemUser
from app.schemas.dashboard import (
    AnomalyTrendPoint,
    DashboardSummary,
    DistributionSlice,
    RecentAnomalyItem,
    TopIP,
)
from app.services import dashboard_service


router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardSummary,
)
def dashboard_summary(
    upload_id: int | None = Query(default=None),
    scope: str = Query(default="latest", pattern="^(latest|combined|all)$"),
    db: Session = Depends(get_db),
    current_user: SystemUser = Depends(get_current_user),
):
    upload_ids = dashboard_service.resolve_upload_ids(db, upload_id, scope)
    return dashboard_service.get_summary(db, upload_ids=upload_ids)


@router.get(
    "/recent-anomalies",
    response_model=list[RecentAnomalyItem],
)
def recent_anomalies(
    limit: int = Query(default=20, ge=1, le=100),
    hours: int | None = Query(default=24, description="Time window in hours; omit/0 for no limit"),
    upload_id: int | None = Query(default=None),
    scope: str = Query(default="latest", pattern="^(latest|combined|all)$"),
    db: Session = Depends(get_db),
    current_user: SystemUser = Depends(get_current_user),
):
    upload_ids = dashboard_service.resolve_upload_ids(db, upload_id, scope)
    return dashboard_service.get_recent_anomalies(
        db,
        limit=limit,
        upload_ids=upload_ids,
        hours=hours if hours and hours > 0 else None,
    )


@router.get(
    "/anomaly-trends",
    response_model=list[AnomalyTrendPoint],
)
def anomaly_trends(
    days: int = Query(default=14, ge=1, le=90),
    upload_id: int | None = Query(default=None),
    scope: str = Query(default="latest", pattern="^(latest|combined|all)$"),
    db: Session = Depends(get_db),
    current_user: SystemUser = Depends(get_current_user),
):
    upload_ids = dashboard_service.resolve_upload_ids(db, upload_id, scope)
    return dashboard_service.get_anomaly_trends(
        db,
        days=days,
        upload_ids=upload_ids,
    )


@router.get(
    "/top-ips",
    response_model=list[TopIP],
)
def top_ips(
    column: str = Query(
        default="src_ip",
        pattern="^(src_ip|dst_ip)$",
    ),
    limit: int = Query(default=10, ge=1, le=100),
    upload_id: int | None = Query(default=None),
    scope: str = Query(default="latest", pattern="^(latest|combined|all)$"),
    db: Session = Depends(get_db),
    current_user: SystemUser = Depends(get_current_user),
):
    upload_ids = dashboard_service.resolve_upload_ids(db, upload_id, scope)
    return dashboard_service.get_top_ips(
        db,
        column=column,
        limit=limit,
        upload_ids=upload_ids,
    )


@router.get(
    "/protocol-distribution",
    response_model=list[DistributionSlice],
)
def protocol_distribution(
    upload_id: int | None = Query(default=None),
    scope: str = Query(default="latest", pattern="^(latest|combined|all)$"),
    db: Session = Depends(get_db),
    current_user: SystemUser = Depends(get_current_user),
):
    upload_ids = dashboard_service.resolve_upload_ids(db, upload_id, scope)
    return dashboard_service.get_protocol_distribution(db, upload_ids=upload_ids)


@router.get(
    "/rule-type-distribution",
    response_model=list[DistributionSlice],
)
def rule_type_distribution(
    upload_id: int | None = Query(default=None),
    scope: str = Query(default="latest", pattern="^(latest|combined|all)$"),
    db: Session = Depends(get_db),
    current_user: SystemUser = Depends(get_current_user),
):
    upload_ids = dashboard_service.resolve_upload_ids(db, upload_id, scope)
    return dashboard_service.get_rule_type_distribution(db, upload_ids=upload_ids)


@router.get(
    "/top-destination-ports",
    response_model=list[DistributionSlice],
)
def top_destination_ports(
    limit: int = Query(default=10, ge=1, le=100),
    upload_id: int | None = Query(default=None),
    scope: str = Query(default="latest", pattern="^(latest|combined|all)$"),
    db: Session = Depends(get_db),
    current_user: SystemUser = Depends(get_current_user),
):
    upload_ids = dashboard_service.resolve_upload_ids(db, upload_id, scope)
    return dashboard_service.get_top_destination_ports(
        db,
        limit=limit,
        upload_ids=upload_ids,
    )


@router.get(
    "/firewall-rule-activity",
    response_model=list[DistributionSlice],
)
def firewall_rule_activity(
    limit: int = Query(default=10, ge=1, le=100),
    upload_id: int | None = Query(default=None),
    scope: str = Query(default="latest", pattern="^(latest|combined|all)$"),
    db: Session = Depends(get_db),
    current_user: SystemUser = Depends(get_current_user),
):
    upload_ids = dashboard_service.resolve_upload_ids(db, upload_id, scope)
    return dashboard_service.get_firewall_rule_activity(
        db,
        limit=limit,
        upload_ids=upload_ids,
    )
