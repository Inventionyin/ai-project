from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.workspace import WorkspaceSummaryData
from app.services.workspace import get_workspace_summary

router = APIRouter(prefix="/projects")


@router.get("/{projectId}/workspace/summary", response_model=ApiResponse[WorkspaceSummaryData])
async def workspace_summary(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[WorkspaceSummaryData]:
    data = await get_workspace_summary(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)
