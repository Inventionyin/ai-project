from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.executor import ExecutorCreateRequest, ExecutorDetail, ExecutorUpdateRequest
from app.services.executor import (
    create_executor,
    delete_executor,
    get_executor,
    list_executors,
    update_executor,
)

router = APIRouter(prefix="/projects/{projectId}/executors")


@router.post("", response_model=ApiResponse[ExecutorDetail])
async def create_executor_endpoint(
    projectId: uuid.UUID,
    body: ExecutorCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ExecutorDetail]:
    result = await create_executor(
        db, user=user, project_id=projectId,
        name=body.name, executor_type=body.executorType,
        description=body.description, config=body.config, version=body.version,
    )
    return ApiResponse(data=result, requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[ExecutorDetail]])
async def list_executors_endpoint(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[ExecutorDetail]]:
    total, items = await list_executors(db, user=user, project_id=projectId, page=page, page_size=pageSize)
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/{executorId}", response_model=ApiResponse[ExecutorDetail])
async def get_executor_endpoint(
    projectId: uuid.UUID,
    executorId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ExecutorDetail]:
    result = await get_executor(db, user=user, project_id=projectId, executor_id=executorId)
    return ApiResponse(data=result, requestId=request_id)


@router.put("/{executorId}", response_model=ApiResponse[ExecutorDetail])
async def update_executor_endpoint(
    projectId: uuid.UUID,
    executorId: uuid.UUID,
    body: ExecutorUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ExecutorDetail]:
    result = await update_executor(
        db, user=user, project_id=projectId, executor_id=executorId,
        name=body.name, description=body.description,
        config=body.config, enabled=body.enabled, version=body.version,
    )
    return ApiResponse(data=result, requestId=request_id)


@router.delete("/{executorId}", response_model=ApiResponse)
async def delete_executor_endpoint(
    projectId: uuid.UUID,
    executorId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse:
    await delete_executor(db, user=user, project_id=projectId, executor_id=executorId)
    return ApiResponse(requestId=request_id)
