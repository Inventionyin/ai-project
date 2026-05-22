from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.services.security_policy import list_audit_logs

router = APIRouter(prefix="/projects/{projectId}/security")


@router.get("/audit-logs", response_model=ApiResponse)
async def get_audit_logs(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    module: str | None = None,
    action: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse:
    total, items = await list_audit_logs(
        db, user=user, project_id=projectId, page=page, page_size=pageSize,
        module=module, action=action,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)
