from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectMember
from app.models.user import User
from app.models.enums import ProjectRole
from app.api.deps import CurrentUser


async def list_members(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> tuple[int, list[dict]]:
    count_q = select(func.count()).select_from(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.tenant_id == user.tenant_id,
    )
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.tenant_id == user.tenant_id,
        )
        .order_by(ProjectMember.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(q)).all()

    items = []
    for pm, u in rows:
        items.append({
            "id": str(pm.id),
            "userId": str(pm.user_id),
            "userName": u.name or u.username or "",
            "userEmail": u.email or "",
            "role": pm.role.value if hasattr(pm.role, 'value') else str(pm.role),
            "createdAt": int(pm.created_at.timestamp()) if pm.created_at else None,
        })
    return total, items


async def add_member(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = "VIEWER",
) -> ProjectMember:
    existing = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if existing:
        raise ValueError("User is already a member of this project")

    target_user = await db.scalar(select(User).where(User.id == user_id))
    if not target_user:
        raise ValueError("User not found")

    try:
        project_role = ProjectRole(role)
    except ValueError:
        project_role = ProjectRole.VIEWER

    pm = ProjectMember(
        tenant_id=user.tenant_id,
        project_id=project_id,
        user_id=user_id,
        role=project_role,
    )
    db.add(pm)
    await db.flush()
    return pm


async def update_member_role(
    db: AsyncSession,
    *,
    member_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
) -> ProjectMember:
    pm = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.id == member_id,
            ProjectMember.tenant_id == tenant_id,
        )
    )
    if not pm:
        raise ValueError("Member not found")

    try:
        project_role = ProjectRole(role)
    except ValueError:
        project_role = ProjectRole.VIEWER

    pm.role = project_role
    await db.flush()
    return pm


async def remove_member(
    db: AsyncSession,
    *,
    member_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    pm = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.id == member_id,
            ProjectMember.tenant_id == tenant_id,
        )
    )
    if not pm:
        raise ValueError("Member not found")
    await db.delete(pm)
    await db.flush()


async def list_users_for_add(
    db: AsyncSession,
    *,
    user: CurrentUser,
    query: str = "",
) -> list[dict]:
    q = select(User).where(User.tenant_id == user.tenant_id)
    if query:
        q = q.where(User.name.ilike(f"%{query}%") | User.email.ilike(f"%{query}%"))
    q = q.limit(20)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": str(u.id), "name": u.name or u.username or "", "email": u.email or ""}
        for u in rows
    ]
