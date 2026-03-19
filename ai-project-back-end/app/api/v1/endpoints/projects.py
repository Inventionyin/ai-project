from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDetailData,
    ProjectHomeStatsData,
    ProjectListItem,
    ProjectUpdateRequest,
)
from app.services.project import (
    create_project,
    delete_project,
    get_home_stats,
    get_project_metrics,
    get_project,
    list_projects,
    update_project,
)

router = APIRouter(prefix="/projects")


def _parse_uuid(value: str, *, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field}") from exc


def _to_project_detail(project, member_count: int) -> ProjectDetailData:
    return ProjectDetailData(
        id=str(project.id),
        name=project.name,
        description=project.description,
        ownerId=str(project.owner_id),
        memberCount=member_count,
        createdAt=to_unix_ts(project.created_at),
    )


@router.post("", response_model=ApiResponse[ProjectDetailData])
async def create(
    payload: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectDetailData]:
    try:
        project = await create_project(
            db,
            user=user,
            name=payload.name,
            description=payload.description,
            owner_id=_parse_uuid(payload.ownerId, field="ownerId"),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    project, member_count = await get_project(db, user=user, project_id=project.id)
    return ApiResponse(data=_to_project_detail(project, member_count), requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[ProjectListItem]])
async def list_(
    page: int = 1,
    pageSize: int = 20,
    keyword: str | None = None,
    key: str | None = None,
    id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[ProjectListItem]]:
    if keyword is None and key:
        keyword = key

    if id:
        project_id = _parse_uuid(id, field="id")
        project, member_count = await get_project(db, user=user, project_id=project_id)
        case_count, pass_rate = await get_project_metrics(db, user=user, project_id=project_id)
        item = ProjectListItem(
            id=str(project.id),
            name=project.name,
            description=project.description,
            ownerId=str(project.owner_id),
            memberCount=member_count,
            caseCount=case_count,
            passRate=pass_rate,
            createdAt=to_unix_ts(project.created_at),
        )
        return ApiResponse(
            data=PageData(page=1, pageSize=1, total=1, items=[item]),
            requestId=request_id,
        )

    total, rows = await list_projects(db, user=user, page=page, page_size=pageSize, keyword=keyword)
    items = [
        ProjectListItem(
            id=str(p.id),
            name=p.name,
            description=p.description,
            ownerId=str(p.owner_id),
            memberCount=member_count,
            caseCount=case_count,
            passRate=pass_rate,
            createdAt=to_unix_ts(p.created_at),
        )
        for p, member_count, case_count, pass_rate in rows
    ]
    return ApiResponse(
        data=PageData(page=page, pageSize=pageSize, total=total, items=items),
        requestId=request_id,
    )


@router.get("/home-stats", response_model=ApiResponse[ProjectHomeStatsData])
async def home_stats(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectHomeStatsData]:
    project_total, testcase_total, today_run_total, today_pass_rate = await get_home_stats(db, user=user)
    return ApiResponse(
        data=ProjectHomeStatsData(
            projectTotal=project_total,
            testcaseTotal=testcase_total,
            todayRunTotal=today_run_total,
            todayPassRate=today_pass_rate,
        ),
        requestId=request_id,
    )


@router.get("/{id}", response_model=ApiResponse[ProjectDetailData])
async def get(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectDetailData]:
    project, member_count = await get_project(db, user=user, project_id=id)
    return ApiResponse(data=_to_project_detail(project, member_count), requestId=request_id)


@router.put("/{id}", response_model=ApiResponse[ProjectDetailData])
async def update(
    id: uuid.UUID,
    payload: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectDetailData]:
    try:
        project, member_count = await update_project(
            db,
            user=user,
            project_id=id,
            name=payload.name,
            description=payload.description,
            owner_id=_parse_uuid(payload.ownerId, field="ownerId") if payload.ownerId else None,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_project_detail(project, member_count), requestId=request_id)


@router.put("", response_model=ApiResponse[ProjectDetailData])
async def update_by_query(
    id: uuid.UUID,
    payload: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ProjectDetailData]:
    return await update(id, payload, db, user, request_id)


@router.delete("/{id}", response_model=ApiResponse[dict])
async def delete(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_project(db, user=user, project_id=id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)


@router.delete("", response_model=ApiResponse[dict])
async def delete_by_query(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_project(db, user=user, project_id=id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)
