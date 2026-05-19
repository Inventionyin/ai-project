from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.defect_provider import (
    DefectProviderConfigCreateRequest,
    DefectProviderConfigDetail,
)
from app.services.defect_provider import (
    create_defect_provider,
    delete_defect_provider,
    list_defect_providers,
)
from app.services.project import _require_project_write, get_project

router = APIRouter()


@router.get("", response_model=ApiResponse[list[DefectProviderConfigDetail]])
async def list_(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
):
    items = await list_defect_providers(db, user=user, project_id=projectId)
    return ApiResponse(
        data=[
            DefectProviderConfigDetail(
                id=str(i.id),
                projectId=str(i.project_id),
                provider=i.provider,
                name=i.name,
                baseUrl=i.base_url,
                enabled=i.enabled,
                syncStatus=i.sync_status,
                lastSyncAt=int(i.last_sync_at.timestamp()) if i.last_sync_at else None,
                lastError=i.last_error,
            )
            for i in items
        ],
        requestId=request_id,
    )


@router.post("", response_model=ApiResponse[DefectProviderConfigDetail])
async def create_(
    projectId: uuid.UUID,
    payload: DefectProviderConfigCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
):
    project, _ = await get_project(db, user=user, project_id=projectId)
    await _require_project_write(db, user=user, project=project)
    cfg = await create_defect_provider(
        db,
        user=user,
        project_id=projectId,
        provider=payload.provider,
        name=payload.name,
        base_url=payload.baseUrl,
        auth_json={"apiToken": payload.apiToken, "username": payload.username},
        config_json={"projectKey": payload.projectKey},
    )
    await db.commit()
    return ApiResponse(
        data=DefectProviderConfigDetail(
            id=str(cfg.id),
            projectId=str(cfg.project_id),
            provider=cfg.provider,
            name=cfg.name,
            baseUrl=cfg.base_url,
            enabled=cfg.enabled,
            syncStatus=cfg.sync_status,
            lastSyncAt=None,
            lastError=None,
        ),
        requestId=request_id,
    )


@router.delete("/{configId}")
async def delete_(
    projectId: uuid.UUID,
    configId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
):
    project, _ = await get_project(db, user=user, project_id=projectId)
    await _require_project_write(db, user=user, project=project)
    try:
        await delete_defect_provider(db, config_id=configId, tenant_id=user.tenant_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ApiResponse(data={"ok": True}, requestId=request_id)
