from __future__ import annotations

import uuid

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.dashboard import (
    DashboardFailureTopData,
    DashboardQualityGateData,
    DashboardSummaryData,
    DashboardTrialOperationData,
    DashboardTrialOperationReportData,
    DashboardTrialOperationReportSnapshotCreateRequest,
    DashboardTrialOperationReportSnapshotData,
    DashboardTrendData,
)
from app.services.dashboard import (
    create_dashboard_trial_operation_report_snapshot,
    get_dashboard_failure_top,
    get_dashboard_quality_gate,
    get_dashboard_summary,
    get_dashboard_trial_operation,
    get_dashboard_trial_operation_report,
    get_dashboard_trial_operation_report_snapshot,
    get_dashboard_trend,
    list_dashboard_trial_operation_report_snapshots,
)

router = APIRouter(prefix="/projects")


@router.get("/{projectId}/dashboard/summary", response_model=ApiResponse[DashboardSummaryData])
async def summary(
    projectId: uuid.UUID,
    summaryDate: date | None = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DashboardSummaryData]:
    data = await get_dashboard_summary(db, user=user, project_id=projectId, target_date=summaryDate)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/{projectId}/dashboard/failure-top", response_model=ApiResponse[DashboardFailureTopData])
async def failure_top(
    projectId: uuid.UUID,
    dimension: str | None = Query(default="testcase"),
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DashboardFailureTopData]:
    data = await get_dashboard_failure_top(
        db,
        user=user,
        project_id=projectId,
        dimension=dimension,
        days=days,
        limit=limit,
    )
    return ApiResponse(data=data, requestId=request_id)


@router.get("/{projectId}/dashboard/trend", response_model=ApiResponse[DashboardTrendData])
async def trend(
    projectId: uuid.UUID,
    days: int = Query(default=7),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DashboardTrendData]:
    data = await get_dashboard_trend(db, user=user, project_id=projectId, days=days)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/{projectId}/dashboard/quality-gate", response_model=ApiResponse[DashboardQualityGateData])
async def quality_gate(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DashboardQualityGateData]:
    data = await get_dashboard_quality_gate(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/{projectId}/dashboard/trial-operation", response_model=ApiResponse[DashboardTrialOperationData])
async def trial_operation(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DashboardTrialOperationData]:
    data = await get_dashboard_trial_operation(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/{projectId}/dashboard/trial-operation/report", response_model=ApiResponse[DashboardTrialOperationReportData])
async def trial_operation_report(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DashboardTrialOperationReportData]:
    data = await get_dashboard_trial_operation_report(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)


@router.post(
    "/{projectId}/dashboard/trial-operation/report/snapshots",
    response_model=ApiResponse[DashboardTrialOperationReportSnapshotData],
)
@router.post(
    "/{projectId}/dashboard/trial-operation/report-snapshots",
    response_model=ApiResponse[DashboardTrialOperationReportSnapshotData],
    include_in_schema=False,
)
async def create_trial_operation_report_snapshot(
    projectId: uuid.UUID,
    payload: DashboardTrialOperationReportSnapshotCreateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DashboardTrialOperationReportSnapshotData]:
    try:
        data = await create_dashboard_trial_operation_report_snapshot(
            db,
            user=user,
            project_id=projectId,
            payload=payload,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get(
    "/{projectId}/dashboard/trial-operation/report/snapshots",
    response_model=ApiResponse[PageData[DashboardTrialOperationReportSnapshotData]],
)
@router.get(
    "/{projectId}/dashboard/trial-operation/report-snapshots",
    response_model=ApiResponse[PageData[DashboardTrialOperationReportSnapshotData]],
    include_in_schema=False,
)
async def list_trial_operation_report_snapshots(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(6, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[DashboardTrialOperationReportSnapshotData]]:
    total, items = await list_dashboard_trial_operation_report_snapshots(
        db,
        user=user,
        project_id=projectId,
        page=page,
        page_size=pageSize,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get(
    "/{projectId}/dashboard/trial-operation/report/snapshots/{snapshotId}",
    response_model=ApiResponse[DashboardTrialOperationReportSnapshotData],
)
@router.get(
    "/{projectId}/dashboard/trial-operation/report-snapshots/{snapshotId}",
    response_model=ApiResponse[DashboardTrialOperationReportSnapshotData],
    include_in_schema=False,
)
async def get_trial_operation_report_snapshot(
    projectId: uuid.UUID,
    snapshotId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DashboardTrialOperationReportSnapshotData]:
    data = await get_dashboard_trial_operation_report_snapshot(
        db,
        user=user,
        project_id=projectId,
        snapshot_id=snapshotId,
    )
    return ApiResponse(data=data, requestId=request_id)
