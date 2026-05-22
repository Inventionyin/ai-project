from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.ops import OpsHealthSummaryData
from app.services.ops_health import build_ops_health_summary

router = APIRouter(prefix="/ops")


@router.get("/health/summary", response_model=ApiResponse[OpsHealthSummaryData])
async def get_ops_health_summary(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[OpsHealthSummaryData]:
    data = await build_ops_health_summary(db, user)
    return ApiResponse(data=data, requestId=request_id)
