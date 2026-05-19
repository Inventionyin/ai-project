from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.member import (
    MemberCreateRequest,
    MemberListItem,
    MemberListData,
    MemberUpdateRequest,
)
from app.services.member import (
    add_member,
    list_members,
    list_users_for_add,
    remove_member,
    update_member_role,
)
from app.services.project import _require_project_write, get_project

router = APIRouter()


@router.get("", response_model=ApiResponse[MemberListData])
async def list_(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[MemberListData]:
    total, items = await list_members(db, user=user, project_id=projectId, page=page, page_size=pageSize)
    return ApiResponse(
        data=MemberListData(items=[MemberListItem(**i) for i in items], total=total),
        requestId=request_id,
    )


@router.post("", response_model=ApiResponse[MemberListItem])
async def create_(
    projectId: uuid.UUID,
    payload: MemberCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[MemberListItem]:
    project, _ = await get_project(db, user=user, project_id=projectId)
    await _require_project_write(db, user=user, project=project)
    try:
        pm = await add_member(
            db, user=user, project_id=projectId,
            user_id=uuid.UUID(payload.userId), role=payload.role,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ApiResponse(
        data=MemberListItem(
            id=str(pm.id), userId=str(pm.user_id), userName="", userEmail="",
            role=pm.role.value if hasattr(pm.role, 'value') else str(pm.role),
            createdAt=int(pm.created_at.timestamp()) if pm.created_at else None,
        ),
        requestId=request_id,
    )


@router.put("/{memberId}", response_model=ApiResponse[MemberListItem])
async def update_(
    projectId: uuid.UUID,
    memberId: uuid.UUID,
    payload: MemberUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[MemberListItem]:
    project, _ = await get_project(db, user=user, project_id=projectId)
    await _require_project_write(db, user=user, project=project)
    try:
        pm = await update_member_role(db, member_id=memberId, tenant_id=user.tenant_id, role=payload.role)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ApiResponse(
        data=MemberListItem(
            id=str(pm.id), userId=str(pm.user_id), userName="", userEmail="",
            role=pm.role.value if hasattr(pm.role, 'value') else str(pm.role),
            createdAt=int(pm.created_at.timestamp()) if pm.created_at else None,
        ),
        requestId=request_id,
    )


@router.delete("/{memberId}")
async def delete_(
    projectId: uuid.UUID,
    memberId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    project, _ = await get_project(db, user=user, project_id=projectId)
    await _require_project_write(db, user=user, project=project)
    try:
        await remove_member(db, member_id=memberId, tenant_id=user.tenant_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ApiResponse(data={"ok": True}, requestId=request_id)


@router.get("/users", response_model=ApiResponse[list[dict]])
async def list_users_(
    projectId: uuid.UUID,
    q: str = Query("", description="Search by name or email"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[dict]]:
    users = await list_users_for_add(db, user=user, query=q)
    return ApiResponse(data=users, requestId=request_id)
