from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.ai_training import (
    AiTrainingDatasetCreateRequest,
    AiTrainingDatasetListItem,
    AiTrainingJobCreateRequest,
    AiTrainingJobDetail,
    AiTrainingJobListItem,
    AiTrainingJobProgress,
    AiTrainingJobUpdateRequest,
)
from app.schemas.common import ApiResponse, PageData
from app.services.ai_training import (
    create_dataset,
    create_training_job,
    delete_training_job,
    get_training_job,
    get_training_progress,
    list_datasets,
    list_training_jobs,
    prepare_dataset,
    start_training,
    update_training_job,
)

router = APIRouter(prefix="/projects/{projectId}/ai-training")


@router.post("/jobs", response_model=ApiResponse[AiTrainingJobDetail])
async def api_create_training_job(
    projectId: uuid.UUID,
    payload: AiTrainingJobCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiTrainingJobDetail]:
    try:
        data = await create_training_job(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/jobs", response_model=ApiResponse[PageData[AiTrainingJobListItem]])
async def api_list_training_jobs(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[AiTrainingJobListItem]]:
    total, items = await list_training_jobs(
        db, user=user, project_id=projectId, page=page, page_size=pageSize, status=status,
    )
    return ApiResponse(
        data=PageData(page=page, pageSize=pageSize, total=total, items=items),
        requestId=request_id,
    )


@router.get("/jobs/{jobId}", response_model=ApiResponse[AiTrainingJobDetail])
async def api_get_training_job(
    projectId: uuid.UUID,
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiTrainingJobDetail]:
    data = await get_training_job(db, user=user, project_id=projectId, job_id=jobId)
    return ApiResponse(data=data, requestId=request_id)


@router.put("/jobs/{jobId}", response_model=ApiResponse[AiTrainingJobDetail])
async def api_update_training_job(
    projectId: uuid.UUID,
    jobId: uuid.UUID,
    payload: AiTrainingJobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiTrainingJobDetail]:
    try:
        data = await update_training_job(
            db, user=user, project_id=projectId, job_id=jobId, payload=payload,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.delete("/jobs/{jobId}", response_model=ApiResponse[None])
async def api_delete_training_job(
    projectId: uuid.UUID,
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[None]:
    try:
        await delete_training_job(db, user=user, project_id=projectId, job_id=jobId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=None, requestId=request_id)


@router.post("/jobs/{jobId}/prepare", response_model=ApiResponse[AiTrainingJobDetail])
async def api_prepare_dataset(
    projectId: uuid.UUID,
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiTrainingJobDetail]:
    try:
        data = await prepare_dataset(db, user=user, project_id=projectId, job_id=jobId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.post("/jobs/{jobId}/start", response_model=ApiResponse[AiTrainingJobDetail])
async def api_start_training(
    projectId: uuid.UUID,
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiTrainingJobDetail]:
    try:
        data = await start_training(db, user=user, project_id=projectId, job_id=jobId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/jobs/{jobId}/progress", response_model=ApiResponse[AiTrainingJobProgress])
async def api_get_training_progress(
    projectId: uuid.UUID,
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiTrainingJobProgress]:
    data = await get_training_progress(db, user=user, project_id=projectId, job_id=jobId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/datasets", response_model=ApiResponse[AiTrainingDatasetListItem])
async def api_create_dataset(
    projectId: uuid.UUID,
    payload: AiTrainingDatasetCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[AiTrainingDatasetListItem]:
    try:
        data = await create_dataset(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/datasets", response_model=ApiResponse[PageData[AiTrainingDatasetListItem]])
async def api_list_datasets(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[AiTrainingDatasetListItem]]:
    total, items = await list_datasets(
        db, user=user, project_id=projectId, page=page, page_size=pageSize,
    )
    return ApiResponse(
        data=PageData(page=page, pageSize=pageSize, total=total, items=items),
        requestId=request_id,
    )
