from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.schemas.api_target import ApiTargetCreateRequest, ApiTargetDetail, ApiTargetListItem, ApiTargetUpdateRequest
from app.schemas.common import ApiResponse, PageData
from app.services.api_target import create_api_target, delete_api_target, list_api_targets, update_api_target

router = APIRouter(prefix="/api-targets")


def _to_item(target) -> ApiTargetListItem:
    return ApiTargetListItem(
        id=str(target.id),
        projectId=str(target.project_id),
        name=target.name,
        baseUrl=target.base_url,
        defaultMethod=target.default_method,
        defaultPath=target.default_path,
        headers=dict(target.headers_json or {}),
        authRef=dict(target.auth_ref_json or {}),
        timeoutMs=target.timeout_ms,
        enabled=target.enabled,
        version=target.version,
        updatedAt=to_unix_ts(target.updated_at),
    )


@router.get("", response_model=ApiResponse[PageData[ApiTargetListItem]])
async def list_(
    projectId: str = Query(...),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[ApiTargetListItem]]:
    total, rows = await list_api_targets(
        db,
        user=user,
        project_id=uuid.UUID(projectId),
        page=page,
        page_size=pageSize,
    )
    return ApiResponse(
        data=PageData(
            page=page,
            pageSize=pageSize,
            total=total,
            items=[_to_item(item) for item in rows],
        ),
        requestId=request_id,
    )


@router.post("", response_model=ApiResponse[ApiTargetDetail])
async def create_(
    payload: ApiTargetCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiTargetDetail]:
    try:
        target = await create_api_target(db, user=user, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    item = _to_item(target)
    return ApiResponse(data=ApiTargetDetail(**item.model_dump(), createdAt=to_unix_ts(target.created_at)), requestId=request_id)


@router.put("/{id}", response_model=ApiResponse[ApiTargetDetail])
async def update_(
    id: uuid.UUID,
    payload: ApiTargetUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ApiTargetDetail]:
    try:
        target = await update_api_target(db, user=user, api_target_id=id, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    item = _to_item(target)
    return ApiResponse(data=ApiTargetDetail(**item.model_dump(), createdAt=to_unix_ts(target.created_at)), requestId=request_id)


@router.delete("/{id}", response_model=ApiResponse[dict])
async def delete_(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_api_target(db, user=user, api_target_id=id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)
