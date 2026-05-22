from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.testcase_binding import (
    TestcaseBindingCreateRequest,
    TestcaseBindingDetail,
    TestcaseBindingListItem,
    TestcaseBindingUpdateRequest,
)
from app.services.testcase_binding import (
    create_testcase_binding,
    delete_testcase_binding,
    list_testcase_bindings,
    list_testcase_bindings_by_collection,
    list_testcase_bindings_by_request,
    update_testcase_binding,
)

router = APIRouter()


def _to_item(binding) -> TestcaseBindingListItem:
    return TestcaseBindingListItem(
        id=str(binding.id),
        projectId=str(binding.project_id),
        testcaseId=str(binding.testcase_id),
        name=binding.name,
        linkType=binding.link_type,
        datasetId=str(binding.dataset_id) if binding.dataset_id else None,
        apiTargetId=str(binding.api_target_id) if binding.api_target_id else None,
        requestId=str(binding.request_id) if binding.request_id else None,
        collectionId=str(binding.collection_id) if binding.collection_id else None,
        sourceType=binding.source_type,
        assertSummary=binding.assert_summary,
        lastRunStatus=binding.last_run_status,
        lastRunAt=to_unix_ts(binding.last_run_at) if binding.last_run_at else None,
        params=dict(binding.params_json or {}),
        priority=binding.priority,
        enabled=binding.enabled,
        version=binding.version,
        updatedAt=to_unix_ts(binding.updated_at),
    )


@router.get("/testcases/{testcaseId}/bindings", response_model=ApiResponse[PageData[TestcaseBindingListItem]])
async def list_(
    testcaseId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[TestcaseBindingListItem]]:
    total, rows = await list_testcase_bindings(
        db,
        user=user,
        testcase_id=testcaseId,
        page=page,
        page_size=pageSize,
    )
    return ApiResponse(
        data=PageData(page=page, pageSize=pageSize, total=total, items=[_to_item(item) for item in rows]),
        requestId=request_id,
    )


@router.get("/projects/{projectId}/requests/{requestId}/bindings", response_model=ApiResponse[list[TestcaseBindingListItem]])
async def list_by_request(
    projectId: uuid.UUID,
    requestId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[TestcaseBindingListItem]]:
    rows = await list_testcase_bindings_by_request(db, user=user, project_id=projectId, request_id=requestId)
    return ApiResponse(data=[_to_item(item) for item in rows], requestId=request_id)


@router.get("/projects/{projectId}/collections/{collectionId}/bindings", response_model=ApiResponse[list[TestcaseBindingListItem]])
async def list_by_collection(
    projectId: uuid.UUID,
    collectionId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[TestcaseBindingListItem]]:
    rows = await list_testcase_bindings_by_collection(db, user=user, project_id=projectId, collection_id=collectionId)
    return ApiResponse(data=[_to_item(item) for item in rows], requestId=request_id)


@router.post("/testcases/{testcaseId}/bindings", response_model=ApiResponse[TestcaseBindingDetail])
async def create_(
    testcaseId: uuid.UUID,
    payload: TestcaseBindingCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestcaseBindingDetail]:
    try:
        binding = await create_testcase_binding(db, user=user, testcase_id=testcaseId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    item = _to_item(binding)
    return ApiResponse(data=TestcaseBindingDetail(**item.model_dump(), createdAt=to_unix_ts(binding.created_at)), requestId=request_id)


@router.put("/testcase-bindings/{bindingId}", response_model=ApiResponse[TestcaseBindingDetail])
async def update_(
    bindingId: uuid.UUID,
    payload: TestcaseBindingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestcaseBindingDetail]:
    try:
        binding = await update_testcase_binding(db, user=user, binding_id=bindingId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    item = _to_item(binding)
    return ApiResponse(data=TestcaseBindingDetail(**item.model_dump(), createdAt=to_unix_ts(binding.created_at)), requestId=request_id)


@router.delete("/testcase-bindings/{bindingId}", response_model=ApiResponse[dict])
async def delete_(
    bindingId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_testcase_binding(db, user=user, binding_id=bindingId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)
