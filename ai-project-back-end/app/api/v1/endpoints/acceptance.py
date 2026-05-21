from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.acceptance import AcceptanceReportData, AcceptanceSummaryData
from app.schemas.common import ApiResponse
from app.services.acceptance import get_acceptance_report, get_acceptance_summary

router = APIRouter(prefix="/projects")


@router.get("/{projectId}/acceptance/summary", response_model=ApiResponse[AcceptanceSummaryData])
async def acceptance_summary(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AcceptanceSummaryData]:
    data = await get_acceptance_summary(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/{projectId}/acceptance/report", response_model=ApiResponse[AcceptanceReportData])
async def acceptance_report(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AcceptanceReportData]:
    data = await get_acceptance_report(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)
