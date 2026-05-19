from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.performance import (
    K6ScriptGenerateRequest,
    PerformanceTestCreateRequest,
    PerformanceTestDetail,
    PerformanceTestRunDetail,
    PerformanceTestUpdateRequest,
    TrendDataPoint,
)
from app.services.performance_test import (
    create_test,
    delete_test,
    generate_k6_script,
    get_test,
    get_trend,
    list_runs,
    list_tests,
    run_test,
    update_test,
)

router = APIRouter(prefix="/projects/{projectId}/performance-tests")


@router.post("", response_model=ApiResponse[PerformanceTestDetail])
async def create_performance_test_endpoint(
    projectId: uuid.UUID,
    body: PerformanceTestCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PerformanceTestDetail]:
    result = await create_test(
        db, user=user, project_id=projectId,
        name=body.name, test_type=body.testType, description=body.description,
        target_url=body.targetUrl, config=body.config,
        script_content=body.scriptContent, tags=body.tags,
    )
    return ApiResponse(data=result, requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[PerformanceTestDetail]])
async def list_performance_tests_endpoint(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[PerformanceTestDetail]]:
    total, items = await list_tests(db, user=user, project_id=projectId, page=page, page_size=pageSize)
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/{testId}", response_model=ApiResponse[PerformanceTestDetail])
async def get_performance_test_endpoint(
    projectId: uuid.UUID,
    testId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PerformanceTestDetail]:
    result = await get_test(db, user=user, project_id=projectId, test_id=testId)
    return ApiResponse(data=result, requestId=request_id)


@router.put("/{testId}", response_model=ApiResponse[PerformanceTestDetail])
async def update_performance_test_endpoint(
    projectId: uuid.UUID,
    testId: uuid.UUID,
    body: PerformanceTestUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PerformanceTestDetail]:
    result = await update_test(
        db, user=user, project_id=projectId, test_id=testId,
        name=body.name, description=body.description, test_type=body.testType,
        target_url=body.targetUrl, config=body.config,
        script_content=body.scriptContent, tags=body.tags,
    )
    return ApiResponse(data=result, requestId=request_id)


@router.delete("/{testId}", response_model=ApiResponse)
async def delete_performance_test_endpoint(
    projectId: uuid.UUID,
    testId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse:
    await delete_test(db, user=user, project_id=projectId, test_id=testId)
    return ApiResponse(requestId=request_id)


@router.post("/{testId}/run", response_model=ApiResponse[PerformanceTestRunDetail])
async def run_performance_test_endpoint(
    projectId: uuid.UUID,
    testId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PerformanceTestRunDetail]:
    result = await run_test(db, user=user, project_id=projectId, test_id=testId)
    return ApiResponse(data=result, requestId=request_id)


@router.get("/{testId}/runs", response_model=ApiResponse[PageData[PerformanceTestRunDetail]])
async def list_performance_test_runs_endpoint(
    projectId: uuid.UUID,
    testId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[PerformanceTestRunDetail]]:
    total, items = await list_runs(db, user=user, test_id=testId, page=page, page_size=pageSize)
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/{testId}/trend", response_model=ApiResponse[list[TrendDataPoint]])
async def get_performance_test_trend_endpoint(
    projectId: uuid.UUID,
    testId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[TrendDataPoint]]:
    result = await get_trend(db, user=user, test_id=testId)
    return ApiResponse(data=result, requestId=request_id)


@router.post("/generate-k6", response_model=ApiResponse[dict])
async def generate_k6_script_endpoint(
    projectId: uuid.UUID,
    body: K6ScriptGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    script = await generate_k6_script(
        test_type=body.testType, target_url=body.targetUrl, config=body.config,
    )
    return ApiResponse(data={"script": script}, requestId=request_id)
