from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.audit import AuditLog
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember

logger = logging.getLogger(__name__)

_SENSITIVE_FIELD_PATTERNS = [
    re.compile(r"(password|secret|token|api_key|apikey|access_key|private_key)", re.IGNORECASE),
]

_MASKED_VALUE = "***REDACTED***"


def mask_sensitive_fields(data: dict) -> dict:
    masked = {}
    for key, value in data.items():
        if any(p.search(key) for p in _SENSITIVE_FIELD_PATTERNS):
            masked[key] = _MASKED_VALUE
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_fields(value)
        else:
            masked[key] = value
    return masked


def mask_sensitive_text(text: str) -> str:
    result = text
    for pattern in _SENSITIVE_FIELD_PATTERNS:
        result = pattern.sub(_MASKED_VALUE, result)
    return result


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_member_role(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> ProjectRole | None:
    return (await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()


async def require_role(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    allowed_roles: set[str],
) -> None:
    if _is_admin(user):
        return
    project = await _get_project(db, user=user, project_id=project_id)
    if project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project_id)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this project")
    if role.value not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Role {role.value} not in allowed roles: {allowed_roles}")


async def require_project_admin(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
) -> None:
    await require_role(db, user=user, project_id=project_id, allowed_roles={"ADMIN", "OWNER"})


async def require_project_editor(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
) -> None:
    await require_role(db, user=user, project_id=project_id, allowed_roles={"ADMIN", "OWNER", "EDITOR"})


async def create_audit_log(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID | None,
    module: str,
    action: str,
    resource_type: str,
    resource_id: str,
    summary: str | None,
    detail: dict | None = None,
) -> AuditLog:
    masked_detail = mask_sensitive_fields(detail) if detail else {}
    row = AuditLog(
        tenant_id=user.tenant_id,
        project_id=project_id,
        user_id=user.id,
        module=module,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=summary,
        detail_json=masked_detail,
    )
    db.add(row)
    await db.flush()
    return row


async def list_audit_logs(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    module: str | None = None,
    action: str | None = None,
) -> tuple[int, list[dict]]:
    project = await _get_project(db, user=user, project_id=project_id)
    if _is_admin(user) or project.owner_id == user.id:
        pass
    else:
        role = await _get_member_role(db, user=user, project_id=project_id)
        if role is None:
            raise HTTPException(status_code=403, detail="No access to this project")
    base = select(AuditLog).where(
        AuditLog.tenant_id == user.tenant_id,
        AuditLog.project_id == project_id,
    )
    if module:
        base = base.where(AuditLog.module == module)
    if action:
        base = base.where(AuditLog.action == action)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(
        base.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    items = [
        {
            "id": str(r.id),
            "projectId": str(r.project_id) if r.project_id else None,
            "userId": str(r.user_id) if r.user_id else None,
            "module": r.module,
            "action": r.action,
            "resourceType": r.resource_type,
            "resourceId": r.resource_id,
            "summary": r.summary,
            "detail": mask_sensitive_fields(dict(r.detail_json or {})),
            "createdAt": int(r.created_at.timestamp()),
        }
        for r in rows
    ]
    return total, items
