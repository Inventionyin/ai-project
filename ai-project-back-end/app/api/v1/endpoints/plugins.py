from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.plugin import (
    PluginCreateRequest,
    PluginDetail,
    PluginInstallationDetail,
    PluginInstallRequest,
    PluginInvokeRequest,
    PluginInvokeResponse,
    PluginInvokeRecordDetail,
    PluginToggleRequest,
    PluginUpdateRequest,
)
from app.services.plugin import (
    create_plugin,
    delete_plugin,
    get_plugin,
    install_plugin,
    invoke_plugin_installation,
    list_plugin_invocations,
    list_installations,
    list_plugins,
    toggle_plugin,
    uninstall_plugin,
    update_plugin,
)

router = APIRouter(prefix="/plugins")
project_router = APIRouter(prefix="/projects/{projectId}/plugins")


@router.post("", response_model=ApiResponse[PluginDetail])
async def create_plugin_endpoint(
    body: PluginCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PluginDetail]:
    result = await create_plugin(
        db, user=user,
        name=body.name, slug=body.slug, version=body.version,
        description=body.description, author=body.author,
        plugin_type=body.pluginType, config_schema=body.configSchema,
        entry_point=body.entryPoint, min_platform_version=body.minPlatformVersion,
        icon_url=body.iconUrl,
    )
    return ApiResponse(data=result, requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[PluginDetail]])
async def list_plugins_endpoint(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[PluginDetail]]:
    total, items = await list_plugins(db, user=user, page=page, page_size=pageSize)
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/{pluginId}", response_model=ApiResponse[PluginDetail])
async def get_plugin_endpoint(
    pluginId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PluginDetail]:
    result = await get_plugin(db, user=user, plugin_id=pluginId)
    return ApiResponse(data=result, requestId=request_id)


@router.put("/{pluginId}", response_model=ApiResponse[PluginDetail])
async def update_plugin_endpoint(
    pluginId: uuid.UUID,
    body: PluginUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PluginDetail]:
    result = await update_plugin(
        db, user=user, plugin_id=pluginId,
        name=body.name, description=body.description,
        version=body.version, config_schema=body.configSchema,
        entry_point=body.entryPoint, enabled=body.enabled,
        icon_url=body.iconUrl,
    )
    return ApiResponse(data=result, requestId=request_id)


@router.delete("/{pluginId}", response_model=ApiResponse)
async def delete_plugin_endpoint(
    pluginId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse:
    await delete_plugin(db, user=user, plugin_id=pluginId)
    return ApiResponse(requestId=request_id)


@project_router.post("/install", response_model=ApiResponse[PluginInstallationDetail])
async def install_plugin_endpoint(
    projectId: uuid.UUID,
    body: PluginInstallRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PluginInstallationDetail]:
    result = await install_plugin(
        db, user=user, project_id=projectId,
        plugin_id=uuid.UUID(body.pluginId), config=body.config,
    )
    return ApiResponse(data=result, requestId=request_id)


@project_router.get("/installations", response_model=ApiResponse[PageData[PluginInstallationDetail]])
async def list_installations_endpoint(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[PluginInstallationDetail]]:
    total, items = await list_installations(db, user=user, project_id=projectId, page=page, page_size=pageSize)
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@project_router.post("/installations/{installationId}/uninstall", response_model=ApiResponse)
async def uninstall_plugin_endpoint(
    projectId: uuid.UUID,
    installationId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse:
    await uninstall_plugin(db, user=user, project_id=projectId, installation_id=installationId)
    return ApiResponse(requestId=request_id)


@project_router.post("/installations/{installationId}/toggle", response_model=ApiResponse[PluginInstallationDetail])
async def toggle_plugin_endpoint(
    projectId: uuid.UUID,
    installationId: uuid.UUID,
    body: PluginToggleRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PluginInstallationDetail]:
    result = await toggle_plugin(
        db, user=user, project_id=projectId,
        installation_id=installationId, enabled=body.enabled,
    )
    return ApiResponse(data=result, requestId=request_id)


@project_router.post("/installations/{installationId}/invoke", response_model=ApiResponse[PluginInvokeResponse])
async def invoke_plugin_endpoint(
    projectId: uuid.UUID,
    installationId: uuid.UUID,
    body: PluginInvokeRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PluginInvokeResponse]:
    result = await invoke_plugin_installation(
        db,
        user=user,
        project_id=projectId,
        installation_id=installationId,
        payload=(body.payload if body else None),
    )
    return ApiResponse(data=result, requestId=request_id)


@project_router.get("/installations/{installationId}/invocations", response_model=ApiResponse[PageData[PluginInvokeRecordDetail]])
async def list_plugin_invocations_endpoint(
    projectId: uuid.UUID,
    installationId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[PluginInvokeRecordDetail]]:
    total, items = await list_plugin_invocations(
        db,
        user=user,
        project_id=projectId,
        installation_id=installationId,
        page=page,
        page_size=pageSize,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)
