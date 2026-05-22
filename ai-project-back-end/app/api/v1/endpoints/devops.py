from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.devops import (
    DevOpsCallbackRequest,
    DevOpsPipelineCreateRequest,
    DevOpsPipelineDetail,
    DevOpsPipelineUpdateRequest,
    DevOpsRunDetail,
    DevOpsTriggerRequest,
)
from app.services.devops import (
    create_pipeline,
    delete_pipeline,
    get_pipeline,
    handle_callback,
    list_pipelines,
    list_runs,
    trigger_pipeline,
    update_pipeline,
)

router = APIRouter(prefix="/projects/{projectId}/devops")


@router.post("/pipelines", response_model=ApiResponse[DevOpsPipelineDetail])
async def create_pipeline_endpoint(
    projectId: uuid.UUID,
    body: DevOpsPipelineCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DevOpsPipelineDetail]:
    try:
        result = await create_pipeline(
            db, user=user, project_id=projectId,
            name=body.name, provider=body.provider,
            repo_full_name=body.repoFullName, workflow_file=body.workflowFile,
            config=body.config, webhook_secret=body.webhookSecret,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=result, requestId=request_id)


@router.get("/pipelines", response_model=ApiResponse[PageData[DevOpsPipelineDetail]])
async def list_pipelines_endpoint(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[DevOpsPipelineDetail]]:
    total, items = await list_pipelines(db, user=user, project_id=projectId, page=page, page_size=pageSize)
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/pipelines/{pipelineId}", response_model=ApiResponse[DevOpsPipelineDetail])
async def get_pipeline_endpoint(
    projectId: uuid.UUID,
    pipelineId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DevOpsPipelineDetail]:
    result = await get_pipeline(db, user=user, project_id=projectId, pipeline_id=pipelineId)
    return ApiResponse(data=result, requestId=request_id)


@router.put("/pipelines/{pipelineId}", response_model=ApiResponse[DevOpsPipelineDetail])
async def update_pipeline_endpoint(
    projectId: uuid.UUID,
    pipelineId: uuid.UUID,
    body: DevOpsPipelineUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DevOpsPipelineDetail]:
    try:
        result = await update_pipeline(
            db, user=user, project_id=projectId, pipeline_id=pipelineId,
            name=body.name, repo_full_name=body.repoFullName,
            workflow_file=body.workflowFile, config=body.config,
            webhook_secret=body.webhookSecret, enabled=body.enabled,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=result, requestId=request_id)


@router.delete("/pipelines/{pipelineId}", response_model=ApiResponse)
async def delete_pipeline_endpoint(
    projectId: uuid.UUID,
    pipelineId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse:
    try:
        await delete_pipeline(db, user=user, project_id=projectId, pipeline_id=pipelineId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(requestId=request_id)


@router.post("/pipelines/{pipelineId}/trigger", response_model=ApiResponse[DevOpsRunDetail])
async def trigger_pipeline_endpoint(
    projectId: uuid.UUID,
    pipelineId: uuid.UUID,
    body: DevOpsTriggerRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DevOpsRunDetail]:
    try:
        result = await trigger_pipeline(
            db, user=user, project_id=projectId, pipeline_id=pipelineId,
            branch=body.branch, commit_sha=body.commitSha, params=body.params,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=result, requestId=request_id)


@router.get("/runs", response_model=ApiResponse[PageData[DevOpsRunDetail]])
async def list_runs_endpoint(
    projectId: uuid.UUID,
    pipelineId: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[DevOpsRunDetail]]:
    total, items = await list_runs(
        db, user=user, project_id=projectId, pipeline_id=pipelineId, page=page, page_size=pageSize,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.post("/callback", response_model=ApiResponse[DevOpsRunDetail])
async def callback_endpoint(
    projectId: uuid.UUID,
    body: DevOpsCallbackRequest,
    request: Request,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DevOpsRunDetail]:
    try:
        result = await handle_callback(
            db,
            project_id=projectId,
            external_run_id=body.externalRunId, status=body.status,
            webhook_secret=x_webhook_secret,
            signature=x_hub_signature_256,
            raw_body=await request.body(),
            commit_sha=body.commitSha, branch=body.branch,
            error_message=body.errorMessage, log_url=body.logUrl, meta=body.meta,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=result, requestId=request_id)
