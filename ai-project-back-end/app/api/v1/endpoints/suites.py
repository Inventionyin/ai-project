from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.suite import (
    SuiteConfig,
    SuiteCreateRequest,
    SuiteItemPublic,
    SuiteItemsUpsertRequest,
    SuitePublic,
    SuitePutRequest,
)
from app.services.suite import (
    create_suite,
    delete_suite,
    get_suite,
    list_suite_items,
    list_suites,
    update_suite,
    upsert_suite_items,
)

router = APIRouter(prefix="/suites")


def _suite_config_from_json(config_json: dict | None) -> SuiteConfig:
    cfg = dict(config_json or {})
    allowed = {"timeoutSec", "concurrency", "retryCount", "retryOnlyOn", "failFast", "variables"}
    filtered = {k: cfg[k] for k in allowed if k in cfg}
    return SuiteConfig(**filtered)


def _to_public(suite) -> SuitePublic:
    cfg = dict(suite.config_json or {})
    default_env_id = cfg.get("defaultEnvId")
    return SuitePublic(
        id=str(suite.id),
        projectId=str(suite.project_id),
        name=suite.name,
        defaultEnvId=str(default_env_id) if default_env_id else None,
        config=_suite_config_from_json(cfg),
        createdAt=to_unix_ts(suite.created_at),
        updatedAt=to_unix_ts(suite.updated_at),
    )


def _to_item_public(item, testcase) -> SuiteItemPublic:
    return SuiteItemPublic(
        id=str(item.id),
        suiteId=str(item.suite_id),
        testcaseId=str(item.testcase_id),
        orderNo=item.order_no,
        params=dict(item.params_json or {}),
        testcaseTitle=testcase.title,
        testcaseType=testcase.type,
        testcasePriority=testcase.priority,
        testcaseStatus=testcase.status,
    )


@router.post("", response_model=ApiResponse[SuitePublic])
async def create(
    payload: SuiteCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[SuitePublic]:
    try:
        suite = await create_suite(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            name=payload.name,
            config=payload.config.model_dump(),
            default_env_id=payload.defaultEnvId,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    suite = await get_suite(db, user=user, suite_id=suite.id)
    return ApiResponse(data=_to_public(suite), requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[SuitePublic]])
async def list_(
    projectId: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[SuitePublic]]:
    project_uuid = uuid.UUID(projectId) if projectId else None

    total, suites = await list_suites(db, user=user, project_id=project_uuid, page=page, page_size=pageSize)
    items = [_to_public(s) for s in suites]
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/{id}", response_model=ApiResponse[SuitePublic])
async def get(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[SuitePublic]:
    suite = await get_suite(db, user=user, suite_id=id)
    return ApiResponse(data=_to_public(suite), requestId=request_id)


@router.put("/{id}", response_model=ApiResponse[SuitePublic])
async def update(
    id: uuid.UUID,
    payload: SuitePutRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[SuitePublic]:
    try:
        suite = await update_suite(
            db,
            user=user,
            suite_id=id,
            project_id=uuid.UUID(payload.projectId),
            name=payload.name,
            config=payload.config.model_dump(),
            default_env_id=payload.defaultEnvId,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    suite = await get_suite(db, user=user, suite_id=suite.id)
    return ApiResponse(data=_to_public(suite), requestId=request_id)


@router.delete("/{id}", response_model=ApiResponse[dict])
async def delete(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_suite(db, user=user, suite_id=id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)


@router.post("/{suiteId}/items", response_model=ApiResponse[list[SuiteItemPublic]])
async def upsert_items(
    suiteId: uuid.UUID,
    payload: SuiteItemsUpsertRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[SuiteItemPublic]]:
    try:
        await upsert_suite_items(
            db,
            user=user,
            suite_id=suiteId,
            items=[i.model_dump() for i in payload.items],
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    rows = await list_suite_items(db, user=user, suite_id=suiteId)
    return ApiResponse(data=[_to_item_public(i, tc) for i, tc in rows], requestId=request_id)


@router.get("/{suiteId}/items", response_model=ApiResponse[list[SuiteItemPublic]])
async def list_items(
    suiteId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[SuiteItemPublic]]:
    rows = await list_suite_items(db, user=user, suite_id=suiteId)
    return ApiResponse(data=[_to_item_public(i, tc) for i, tc in rows], requestId=request_id)

