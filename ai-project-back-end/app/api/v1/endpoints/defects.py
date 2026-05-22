from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.defect import (
    DefectAssignRequest,
    DefectClusterItem,
    DefectCreateRequest,
    DefectDetail,
    DefectImportRequest,
    DefectImportResult,
    DefectListItem,
    DefectRiskHint,
    DefectTransitionRequest,
)
from app.services.defect import (
    assign_defect,
    create_defect,
    get_defect,
    import_defects,
    list_defect_clusters,
    list_defect_risk_hints,
    list_defects,
    transition_defect,
)

router = APIRouter(prefix="/projects/{projectId}/defects")


@router.post("", response_model=ApiResponse[DefectDetail])
async def create_project_defect(
    projectId: uuid.UUID,
    payload: DefectCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DefectDetail]:
    try:
        data = await create_defect(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[DefectListItem]])
async def list_project_defects(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[DefectListItem]]:
    total, items = await list_defects(
        db,
        user=user,
        project_id=projectId,
        page=page,
        page_size=pageSize,
        status=status,
        q=q,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.post("/import", response_model=ApiResponse[DefectImportResult])
async def import_project_defects(
    projectId: uuid.UUID,
    payload: DefectImportRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DefectImportResult]:
    try:
        data = await import_defects(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/clusters", response_model=ApiResponse[list[DefectClusterItem]])
async def get_project_defect_clusters(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[DefectClusterItem]]:
    data = await list_defect_clusters(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/risk-hints", response_model=ApiResponse[list[DefectRiskHint]])
async def get_project_defect_risk_hints(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[DefectRiskHint]]:
    data = await list_defect_risk_hints(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)


@router.get("/{defectId}", response_model=ApiResponse[DefectDetail])
async def get_project_defect(
    projectId: uuid.UUID,
    defectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DefectDetail]:
    data = await get_defect(db, user=user, project_id=projectId, defect_id=defectId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/{defectId}/assign", response_model=ApiResponse[DefectDetail])
async def assign_project_defect(
    projectId: uuid.UUID,
    defectId: uuid.UUID,
    payload: DefectAssignRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DefectDetail]:
    try:
        assignee_id = uuid.UUID(payload.assigneeId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_assignee_id") from exc
    try:
        data = await assign_defect(
            db,
            user=user,
            project_id=projectId,
            defect_id=defectId,
            assignee_id=assignee_id,
            note=payload.note,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.post("/{defectId}/transition", response_model=ApiResponse[DefectDetail])
async def transition_project_defect(
    projectId: uuid.UUID,
    defectId: uuid.UUID,
    payload: DefectTransitionRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DefectDetail]:
    try:
        data = await transition_defect(db, user=user, project_id=projectId, defect_id=defectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)
