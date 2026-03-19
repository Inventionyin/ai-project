from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.api_target import ApiTarget
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember
from app.schemas.api_target import ApiTargetCreateRequest, ApiTargetUpdateRequest


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_member_role(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> ProjectRole | None:
    return (
        await db.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
                ProjectMember.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()


async def _require_project_read(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No access to this project")


async def _require_project_write(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="Only Owner/Editor can modify this project")


async def get_api_target(
    db: AsyncSession,
    *,
    user: CurrentUser,
    api_target_id: uuid.UUID,
) -> ApiTarget:
    target = await db.scalar(
        select(ApiTarget).where(
            ApiTarget.id == api_target_id,
            ApiTarget.tenant_id == user.tenant_id,
        )
    )
    if target is None:
        raise HTTPException(status_code=404, detail="api_target_not_found")
    project = await _get_project(db, user=user, project_id=target.project_id)
    await _require_project_read(db, user=user, project=project)
    return target


async def list_api_targets(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[int, list[ApiTarget]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base_stmt = select(ApiTarget).where(
        ApiTarget.tenant_id == user.tenant_id,
        ApiTarget.project_id == project_id,
    )
    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)
    rows = (
        (
            await db.execute(
                base_stmt.order_by(desc(ApiTarget.updated_at)).offset((page - 1) * page_size).limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return total, list(rows)


async def create_api_target(
    db: AsyncSession,
    *,
    user: CurrentUser,
    payload: ApiTargetCreateRequest,
) -> ApiTarget:
    project_id = uuid.UUID(payload.projectId)
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    target = ApiTarget(
        tenant_id=user.tenant_id,
        project_id=project_id,
        name=payload.name,
        base_url=payload.baseUrl,
        default_method=payload.defaultMethod.upper() if payload.defaultMethod else None,
        default_path=payload.defaultPath,
        headers_json=dict(payload.headers or {}),
        auth_ref_json=dict(payload.authRef or {}),
        timeout_ms=payload.timeoutMs,
        enabled=payload.enabled,
        version=1,
        created_by=user.id,
    )
    db.add(target)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="api_target_name_conflict") from exc
    return target


async def update_api_target(
    db: AsyncSession,
    *,
    user: CurrentUser,
    api_target_id: uuid.UUID,
    payload: ApiTargetUpdateRequest,
) -> ApiTarget:
    target = await get_api_target(db, user=user, api_target_id=api_target_id)
    project = await _get_project(db, user=user, project_id=target.project_id)
    await _require_project_write(db, user=user, project=project)

    if target.version != payload.version:
        raise HTTPException(status_code=409, detail="version_conflict")

    target.name = payload.name
    target.base_url = payload.baseUrl
    target.default_method = payload.defaultMethod.upper() if payload.defaultMethod else None
    target.default_path = payload.defaultPath
    target.headers_json = dict(payload.headers or {})
    target.auth_ref_json = dict(payload.authRef or {})
    target.timeout_ms = payload.timeoutMs
    target.enabled = payload.enabled
    target.version += 1
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="api_target_name_conflict") from exc
    return target


async def delete_api_target(
    db: AsyncSession,
    *,
    user: CurrentUser,
    api_target_id: uuid.UUID,
) -> None:
    target = await get_api_target(db, user=user, api_target_id=api_target_id)
    project = await _get_project(db, user=user, project_id=target.project_id)
    await _require_project_write(db, user=user, project=project)
    await db.delete(target)
