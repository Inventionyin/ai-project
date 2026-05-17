from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.enums import ProjectRole
from app.models.executor import Executor
from app.models.project import Project, ProjectMember
from app.schemas.executor import ExecutorDetail
from app.services.platform_record import create_audit_log

logger = logging.getLogger(__name__)


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _require_project_write(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = (await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="No write access to this project")


async def _require_project_read(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = (await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No access to this project")


def _to_detail(row: Executor) -> ExecutorDetail:
    return ExecutorDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        name=row.name,
        executorType=row.executor_type,
        description=row.description,
        config=dict(row.config_json) if row.config_json else None,
        enabled=row.enabled,
        version=row.version,
        createdBy=str(row.created_by) if row.created_by else None,
        createdAt=int(row.created_at.timestamp()),
        updatedAt=int(row.updated_at.timestamp()),
    )


async def create_executor(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    name: str, executor_type: str, description: str | None = None,
    config: dict | None = None, version: str | None = None,
) -> ExecutorDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = Executor(
        tenant_id=user.tenant_id, project_id=project_id, name=name,
        executor_type=executor_type, description=description,
        config_json=config, version=version, created_by=user.id,
    )
    db.add(row)
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        action="CREATE_EXECUTOR", resource_type="executor",
        resource_id=str(row.id), summary=f"创建执行器: {name} ({executor_type})",
    )
    return _to_detail(row)


async def list_executors(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    page: int, page_size: int,
) -> tuple[int, list[ExecutorDetail]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base = select(Executor).where(
        Executor.tenant_id == user.tenant_id,
        Executor.project_id == project_id,
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(base.order_by(desc(Executor.created_at)).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return total, [_to_detail(r) for r in rows]


async def get_executor(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, executor_id: uuid.UUID,
) -> ExecutorDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await db.scalar(select(Executor).where(
        Executor.id == executor_id,
        Executor.project_id == project_id,
        Executor.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Executor not found")
    return _to_detail(row)


async def update_executor(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, executor_id: uuid.UUID,
    **kwargs,
) -> ExecutorDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(select(Executor).where(
        Executor.id == executor_id,
        Executor.project_id == project_id,
        Executor.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Executor not found")
    for key, value in kwargs.items():
        if value is not None:
            if key == "name":
                row.name = value
            elif key == "description":
                row.description = value
            elif key == "config":
                row.config_json = value
            elif key == "enabled":
                row.enabled = value
            elif key == "version":
                row.version = value
    await db.flush()
    return _to_detail(row)


async def delete_executor(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, executor_id: uuid.UUID,
) -> None:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(select(Executor).where(
        Executor.id == executor_id,
        Executor.project_id == project_id,
        Executor.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Executor not found")
    await db.delete(row)
    await db.flush()
