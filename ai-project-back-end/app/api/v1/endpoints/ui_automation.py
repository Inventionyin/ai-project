from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.ui_automation import (
    UiTestGenerateRequest,
    UiTestRecordRequest,
    UiTestRunDetail,
    UiTestRunRequest,
    UiTestScriptCreateRequest,
    UiTestScriptDetail,
    UiTestScriptUpdateRequest,
)
from app.services.ui_automation import (
    create_script,
    delete_script,
    generate_script,
    get_run,
    get_script,
    list_runs,
    list_scripts,
    run_ui_test,
    save_recording,
    update_script,
)

router = APIRouter(prefix="/projects/{projectId}/ui-automation")


@router.post("/scripts", response_model=ApiResponse[UiTestScriptDetail])
async def create_script_endpoint(
    projectId: uuid.UUID,
    body: UiTestScriptCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestScriptDetail]:
    result = await create_script(
        db, user=user, project_id=projectId,
        name=body.name, description=body.description,
        script_type=body.scriptType, browser=body.browser,
        viewport_width=body.viewportWidth, viewport_height=body.viewportHeight,
        base_url=body.baseUrl, tags=body.tags,
    )
    return ApiResponse(data=result, requestId=request_id)


@router.get("/scripts", response_model=ApiResponse[PageData[UiTestScriptDetail]])
async def list_scripts_endpoint(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[UiTestScriptDetail]]:
    total, items = await list_scripts(db, user=user, project_id=projectId, page=page, page_size=pageSize)
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/scripts/{scriptId}", response_model=ApiResponse[UiTestScriptDetail])
async def get_script_endpoint(
    projectId: uuid.UUID,
    scriptId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestScriptDetail]:
    result = await get_script(db, user=user, project_id=projectId, script_id=scriptId)
    return ApiResponse(data=result, requestId=request_id)


@router.put("/scripts/{scriptId}", response_model=ApiResponse[UiTestScriptDetail])
async def update_script_endpoint(
    projectId: uuid.UUID,
    scriptId: uuid.UUID,
    body: UiTestScriptUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestScriptDetail]:
    result = await update_script(
        db, user=user, project_id=projectId, script_id=scriptId,
        name=body.name, description=body.description,
        script_type=body.scriptType, browser=body.browser,
        viewport_width=body.viewportWidth, viewport_height=body.viewportHeight,
        base_url=body.baseUrl, tags=body.tags,
    )
    return ApiResponse(data=result, requestId=request_id)


@router.delete("/scripts/{scriptId}", response_model=ApiResponse)
async def delete_script_endpoint(
    projectId: uuid.UUID,
    scriptId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse:
    await delete_script(db, user=user, project_id=projectId, script_id=scriptId)
    return ApiResponse(requestId=request_id)


@router.post("/scripts/{scriptId}/record", response_model=ApiResponse[UiTestScriptDetail])
async def record_endpoint(
    projectId: uuid.UUID,
    scriptId: uuid.UUID,
    body: UiTestRecordRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestScriptDetail]:
    result = await save_recording(
        db, user=user, project_id=projectId, script_id=scriptId, actions=body.actions,
    )
    return ApiResponse(data=result, requestId=request_id)


@router.post("/scripts/{scriptId}/generate", response_model=ApiResponse[UiTestScriptDetail])
async def generate_endpoint(
    projectId: uuid.UUID,
    scriptId: uuid.UUID,
    body: UiTestGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestScriptDetail]:
    result = await generate_script(db, user=user, project_id=projectId, script_id=scriptId)
    return ApiResponse(data=result, requestId=request_id)


@router.post("/scripts/{scriptId}/run", response_model=ApiResponse[UiTestRunDetail])
async def run_endpoint(
    projectId: uuid.UUID,
    scriptId: uuid.UUID,
    body: UiTestRunRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestRunDetail]:
    result = await run_ui_test(db, user=user, project_id=projectId, script_id=scriptId)
    return ApiResponse(data=result, requestId=request_id)


@router.get("/runs", response_model=ApiResponse[PageData[UiTestRunDetail]])
async def list_runs_endpoint(
    projectId: uuid.UUID,
    scriptId: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[UiTestRunDetail]]:
    total, items = await list_runs(
        db, user=user, project_id=projectId, script_id=scriptId, page=page, page_size=pageSize,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/runs/{runId}", response_model=ApiResponse[UiTestRunDetail])
async def get_run_endpoint(
    projectId: uuid.UUID,
    runId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestRunDetail]:
    result = await get_run(db, user=user, run_id=runId)
    return ApiResponse(data=result, requestId=request_id)
