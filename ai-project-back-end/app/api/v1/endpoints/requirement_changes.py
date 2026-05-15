from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.requirement_change import RequirementChangeSetCreateRequest, RequirementChangeSetDetail, RequirementRegressionSetDetail
from app.services.requirement_change import (
    create_requirement_change_set,
    create_requirement_regression_set,
    get_requirement_change_set,
    get_requirement_regression_set,
    list_requirement_change_sets,
)

router = APIRouter()


@router.post("/projects/{projectId}/requirements/docs/{docId}/change-sets", response_model=ApiResponse[RequirementChangeSetDetail])
async def create_change_set(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    payload: RequirementChangeSetCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementChangeSetDetail]:
    try:
        data = await create_requirement_change_set(db, user=user, project_id=projectId, doc_id=docId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/projects/{projectId}/requirements/docs/{docId}/change-sets", response_model=ApiResponse[list[RequirementChangeSetDetail]])
async def list_change_sets(
    projectId: uuid.UUID,
    docId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[RequirementChangeSetDetail]]:
    data = await list_requirement_change_sets(db, user=user, project_id=projectId, doc_id=docId)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/projects/{projectId}/requirements/change-sets/{changeSetId}", response_model=ApiResponse[RequirementChangeSetDetail])
async def get_change_set(
    projectId: uuid.UUID,
    changeSetId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementChangeSetDetail]:
    data = await get_requirement_change_set(db, user=user, project_id=projectId, change_set_id=changeSetId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/projects/{projectId}/requirements/change-sets/{changeSetId}/regression-set", response_model=ApiResponse[RequirementRegressionSetDetail])
async def create_regression_set(
    projectId: uuid.UUID,
    changeSetId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementRegressionSetDetail]:
    try:
        data = await create_requirement_regression_set(db, user=user, project_id=projectId, change_set_id=changeSetId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/projects/{projectId}/requirements/regression-sets/{regressionSetId}", response_model=ApiResponse[RequirementRegressionSetDetail])
async def get_regression_set(
    projectId: uuid.UUID,
    regressionSetId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RequirementRegressionSetDetail]:
    data = await get_requirement_regression_set(db, user=user, project_id=projectId, regression_set_id=regressionSetId)
    return ApiResponse(data=data, requestId=request_id)
