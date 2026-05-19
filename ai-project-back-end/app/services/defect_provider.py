from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import DefectProviderConfig


async def list_defect_providers(
    db: AsyncSession,
    *,
    user,
    project_id: uuid.UUID,
) -> list[DefectProviderConfig]:
    q = (
        select(DefectProviderConfig)
        .where(
            DefectProviderConfig.project_id == project_id,
            DefectProviderConfig.tenant_id == user.tenant_id,
        )
        .order_by(DefectProviderConfig.created_at.desc())
    )
    return list((await db.execute(q)).scalars().all())


async def create_defect_provider(
    db: AsyncSession,
    *,
    user,
    project_id: uuid.UUID,
    provider: str,
    name: str,
    base_url: str,
    auth_json: dict,
    config_json: dict,
) -> DefectProviderConfig:
    cfg = DefectProviderConfig(
        tenant_id=user.tenant_id,
        project_id=project_id,
        provider=provider,
        name=name,
        base_url=base_url,
        auth_json=auth_json,
        config_json=config_json,
    )
    db.add(cfg)
    await db.flush()
    return cfg


async def update_defect_provider(
    db: AsyncSession,
    *,
    config_id: uuid.UUID,
    tenant_id: uuid.UUID,
    **kwargs,
) -> DefectProviderConfig:
    cfg = await db.scalar(
        select(DefectProviderConfig).where(
            DefectProviderConfig.id == config_id,
            DefectProviderConfig.tenant_id == tenant_id,
        )
    )
    if not cfg:
        raise ValueError("Not found")
    for k, v in kwargs.items():
        if v is not None and hasattr(cfg, k):
            setattr(cfg, k, v)
    await db.flush()
    return cfg


async def delete_defect_provider(
    db: AsyncSession,
    *,
    config_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    cfg = await db.scalar(
        select(DefectProviderConfig).where(
            DefectProviderConfig.id == config_id,
            DefectProviderConfig.tenant_id == tenant_id,
        )
    )
    if not cfg:
        raise ValueError("Not found")
    await db.delete(cfg)
    await db.flush()
