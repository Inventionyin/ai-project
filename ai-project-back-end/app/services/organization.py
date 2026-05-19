from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.organization import Organization
from app.models.project import Project

logger = logging.getLogger(__name__)


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def create_organization(
    db: AsyncSession,
    *,
    user: CurrentUser,
    name: str,
    description: str | None = None,
    settings: dict | None = None,
) -> Organization:
    row = Organization(
        tenant_id=user.tenant_id,
        name=name,
        description=description or "",
        settings_json=settings or {},
    )
    db.add(row)
    await db.flush()
    return row


async def get_organization(
    db: AsyncSession,
    *,
    user: CurrentUser,
    org_id: uuid.UUID,
) -> tuple[Organization, int]:
    row = await db.scalar(select(Organization).where(
        Organization.id == org_id,
        Organization.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    project_count = int((await db.execute(
        select(func.count()).where(
            Project.org_id == org_id,
            Project.tenant_id == user.tenant_id,
        )
    )).scalar_one() or 0)
    return row, project_count


async def list_organizations(
    db: AsyncSession,
    *,
    user: CurrentUser,
    page: int,
    page_size: int,
    keyword: str | None = None,
) -> tuple[int, list[tuple[Organization, int]]]:
    base = select(Organization).where(Organization.tenant_id == user.tenant_id)
    if keyword:
        base = base.where(Organization.name.ilike(f"%{keyword}%"))

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(
        base.order_by(desc(Organization.created_at)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    items = []
    for org in rows:
        project_count = int((await db.execute(
            select(func.count()).where(
                Project.org_id == org.id,
                Project.tenant_id == user.tenant_id,
            )
        )).scalar_one() or 0)
        items.append((org, project_count))

    return total, items


async def update_organization(
    db: AsyncSession,
    *,
    user: CurrentUser,
    org_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
    settings: dict | None = None,
) -> tuple[Organization, int]:
    row = await db.scalar(select(Organization).where(
        Organization.id == org_id,
        Organization.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if name is not None:
        row.name = name
    if description is not None:
        row.description = description
    if settings is not None:
        row.settings_json = settings
    await db.flush()
    project_count = int((await db.execute(
        select(func.count()).where(
            Project.org_id == org_id,
            Project.tenant_id == user.tenant_id,
        )
    )).scalar_one() or 0)
    return row, project_count


async def delete_organization(
    db: AsyncSession,
    *,
    user: CurrentUser,
    org_id: uuid.UUID,
) -> None:
    row = await db.scalar(select(Organization).where(
        Organization.id == org_id,
        Organization.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    # Check for linked projects
    linked = (await db.execute(
        select(Project).where(Project.org_id == org_id, Project.tenant_id == user.tenant_id)
    )).scalars().all()
    if linked:
        raise HTTPException(status_code=400, detail="Organization has linked projects, unlink them first")
    await db.delete(row)
    await db.flush()
