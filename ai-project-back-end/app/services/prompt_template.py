from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember
from app.models.prompt_template import PromptTemplate
from app.schemas.prompt_template import (
    PromptTemplateActivateRequest,
    PromptTemplateCreateRequest,
    PromptTemplateDetail,
    PromptTemplateGovernanceItem,
    PromptTemplateRollbackRequest,
    PromptTemplateRollbackResult,
    PromptTemplateUpdateRequest,
)


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


def _normalize_scene(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_scene")
    return normalized[:64]


def _normalize_name(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_name")
    return normalized[:128]


def _normalize_version(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_version")
    return normalized[:32]


async def _get_project(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_member_role(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> ProjectRole | None:
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


def _to_prompt_template_detail(row: PromptTemplate) -> PromptTemplateDetail:
    return PromptTemplateDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        scene=row.scene,
        name=row.name,
        version=row.version,
        content=row.content,
        variables=dict(row.variables_json or {}),
        isActive=bool(row.is_active),
        createdBy=str(row.created_by) if row.created_by else None,
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


async def _get_template_or_404(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    template_id: uuid.UUID,
) -> PromptTemplate:
    row = await db.scalar(
        select(PromptTemplate).where(
            PromptTemplate.id == template_id,
            PromptTemplate.project_id == project_id,
            PromptTemplate.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return row


async def _deactivate_siblings(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    scene: str,
    name: str,
    current_id: uuid.UUID,
) -> None:
    await db.execute(
        update(PromptTemplate)
        .where(
            PromptTemplate.tenant_id == user.tenant_id,
            PromptTemplate.project_id == project_id,
            PromptTemplate.scene == scene,
            PromptTemplate.name == name,
            PromptTemplate.id != current_id,
        )
        .values(is_active=False)
    )


async def create_prompt_template(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: PromptTemplateCreateRequest,
) -> PromptTemplateDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    scene = _normalize_scene(payload.scene)
    name = _normalize_name(payload.name)
    version = _normalize_version(payload.version)

    exists_row = await db.scalar(
        select(PromptTemplate.id).where(
            PromptTemplate.tenant_id == user.tenant_id,
            PromptTemplate.project_id == project.id,
            PromptTemplate.scene == scene,
            PromptTemplate.name == name,
            PromptTemplate.version == version,
        )
    )
    if exists_row is not None:
        raise HTTPException(status_code=409, detail="prompt_template_version_exists")

    row = PromptTemplate(
        tenant_id=user.tenant_id,
        project_id=project.id,
        scene=scene,
        name=name,
        version=version,
        content=payload.content,
        variables_json=payload.variables,
        is_active=payload.isActive,
        created_by=user.id,
    )
    db.add(row)
    await db.flush()

    if row.is_active:
        await _deactivate_siblings(
            db,
            user=user,
            project_id=project.id,
            scene=row.scene,
            name=row.name,
            current_id=row.id,
        )
        await db.refresh(row)
    return _to_prompt_template_detail(row)


async def list_prompt_templates(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    scene: str | None = None,
    name: str | None = None,
) -> list[PromptTemplateDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    stmt = select(PromptTemplate).where(
        PromptTemplate.tenant_id == user.tenant_id,
        PromptTemplate.project_id == project.id,
    )
    if scene:
        stmt = stmt.where(PromptTemplate.scene == _normalize_scene(scene))
    if name:
        stmt = stmt.where(PromptTemplate.name == _normalize_name(name))

    rows = (await db.execute(stmt.order_by(desc(PromptTemplate.created_at), desc(PromptTemplate.id)))).scalars().all()
    return [_to_prompt_template_detail(row) for row in rows]


async def update_prompt_template(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: PromptTemplateUpdateRequest,
) -> PromptTemplateDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await _get_template_or_404(db, user=user, project_id=project.id, template_id=template_id)

    if payload.content is not None:
        row.content = payload.content
    if payload.variables is not None:
        row.variables_json = payload.variables
    if payload.isActive is not None:
        row.is_active = payload.isActive
    await db.flush()

    if row.is_active:
        await _deactivate_siblings(
            db,
            user=user,
            project_id=project.id,
            scene=row.scene,
            name=row.name,
            current_id=row.id,
        )
        await db.refresh(row)
    return _to_prompt_template_detail(row)


async def activate_prompt_template(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: PromptTemplateActivateRequest,
) -> PromptTemplateDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await _get_template_or_404(db, user=user, project_id=project.id, template_id=template_id)

    row.is_active = payload.isActive
    await db.flush()
    await _deactivate_siblings(
        db,
        user=user,
        project_id=project.id,
        scene=row.scene,
        name=row.name,
        current_id=row.id,
    )
    await db.refresh(row)
    return _to_prompt_template_detail(row)


async def list_prompt_template_governance(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[PromptTemplateGovernanceItem]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    rows = (
        await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.tenant_id == user.tenant_id,
                PromptTemplate.project_id == project.id,
            ).order_by(
                PromptTemplate.scene.asc(),
                PromptTemplate.name.asc(),
                desc(PromptTemplate.created_at),
                desc(PromptTemplate.id),
            )
        )
    ).scalars().all()

    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        key = (row.scene, row.name)
        bucket = grouped.get(key)
        if bucket is None:
            grouped[key] = {
                "scene": row.scene,
                "name": row.name,
                "latestVersion": row.version,
                "activeVersion": row.version if row.is_active else None,
                "versionCount": 1,
            }
            continue
        bucket["versionCount"] = int(bucket["versionCount"]) + 1
        if row.is_active and bucket["activeVersion"] is None:
            bucket["activeVersion"] = row.version

    return [
        PromptTemplateGovernanceItem(
            scene=item["scene"],
            name=item["name"],
            activeVersion=item["activeVersion"],
            latestVersion=item["latestVersion"],
            versionCount=item["versionCount"],
            policy="SINGLE_ACTIVE",
        )
        for item in grouped.values()
    ]


async def rollback_prompt_template(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: PromptTemplateRollbackRequest,
) -> PromptTemplateRollbackResult:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    scene = _normalize_scene(payload.scene)
    name = _normalize_name(payload.name)
    target_version = _normalize_version(payload.targetVersion)

    target = await db.scalar(
        select(PromptTemplate).where(
            PromptTemplate.tenant_id == user.tenant_id,
            PromptTemplate.project_id == project.id,
            PromptTemplate.scene == scene,
            PromptTemplate.name == name,
            PromptTemplate.version == target_version,
        )
    )
    if target is None:
        raise HTTPException(status_code=404, detail="prompt_template_version_not_found")

    target.is_active = True
    await db.flush()
    await _deactivate_siblings(
        db,
        user=user,
        project_id=project.id,
        scene=scene,
        name=name,
        current_id=target.id,
    )

    version_count = (
        await db.scalar(
            select(func.count(PromptTemplate.id)).where(
                PromptTemplate.tenant_id == user.tenant_id,
                PromptTemplate.project_id == project.id,
                PromptTemplate.scene == scene,
                PromptTemplate.name == name,
            )
        )
    ) or 0

    return PromptTemplateRollbackResult(
        scene=scene,
        name=name,
        activeVersion=target.version,
        versionCount=int(version_count),
        policy="SINGLE_ACTIVE",
    )
