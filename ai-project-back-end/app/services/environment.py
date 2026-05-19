from __future__ import annotations

import base64
import json
import uuid
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.models.environment import Environment
from app.models.enums import ProjectRole
from app.models.project import Project, ProjectMember
from app.services.platform_record import create_audit_log


UNSET = object()


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


def _get_fernet() -> Fernet:
    settings = get_settings()
    seed = settings.secrets_encryption_key or settings.jwt_secret_key
    if not seed:
        raise HTTPException(status_code=500, detail="Secrets encryption key is not configured")
    key = base64.urlsafe_b64encode(sha256(seed.encode("utf-8")).digest())
    return Fernet(key)


def _encrypt_secrets(secrets: dict[str, str]) -> str:
    raw = json.dumps(secrets, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _get_fernet().encrypt(raw).decode("utf-8")


def _decrypt_secrets(token: str) -> dict[str, str]:
    if not token:
        return {}
    try:
        raw = _get_fernet().decrypt(token.encode("utf-8"))
    except (InvalidToken, ValueError):
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


def get_secret_keys(env: Environment) -> list[str]:
    if not env.secrets_ref:
        return []
    secrets = _decrypt_secrets(env.secrets_ref)
    return sorted(secrets.keys())


async def _get_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> Project:
    project = (
        await db.execute(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    ).scalar_one_or_none()
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


async def _require_project_read(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project: Project,
) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No access to this project")


async def _require_project_write(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project: Project,
) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="Only Owner/Editor can modify this project")


async def create_environment(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    name: str,
    base_url: str,
    variables: dict[str, str],
    secrets: dict[str, str],
    health_check: dict | None,
) -> Environment:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    secrets_ref: str | None = None
    if secrets:
        secrets_ref = _encrypt_secrets(secrets)
        if len(secrets_ref) > 512:
            raise HTTPException(status_code=400, detail="Secrets too large")

    env = Environment(
        tenant_id=user.tenant_id,
        project_id=project.id,
        name=name,
        base_url=base_url,
        variables_json=variables or {},
        secrets_ref=secrets_ref,
        health_config_json=health_check,
    )
    db.add(env)
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project.id,
        module="environment", action="CREATE_ENVIRONMENT",
        resource_type="environment", resource_id=str(env.id),
        summary=name,
        detail={"base_url": base_url, "variable_count": len(variables or {})},
    )
    return env


async def list_environments(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[Environment]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    rows = (
        await db.execute(
            select(Environment)
            .where(
                Environment.tenant_id == user.tenant_id,
                Environment.project_id == project.id,
            )
            .order_by(Environment.updated_at.desc())
        )
    ).scalars()
    return list(rows.all())


async def get_environment(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    env_id: uuid.UUID,
) -> Environment:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    env = (
        await db.execute(
            select(Environment).where(
                Environment.id == env_id,
                Environment.project_id == project.id,
                Environment.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if env is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    return env


async def update_environment(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    env_id: uuid.UUID,
    name: str | None,
    base_url: str | None,
    variables: dict[str, str] | None,
    secrets: dict[str, str] | None,
    health_check: dict | None | object,
) -> Environment:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    env = (
        await db.execute(
            select(Environment).where(
                Environment.id == env_id,
                Environment.project_id == project.id,
                Environment.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if env is None:
        raise HTTPException(status_code=404, detail="Environment not found")

    if name is not None:
        env.name = name
    if base_url is not None:
        env.base_url = base_url
    if variables is not None:
        env.variables_json = variables
    if secrets is not None:
        if secrets:
            token = _encrypt_secrets(secrets)
            if len(token) > 512:
                raise HTTPException(status_code=400, detail="Secrets too large")
            env.secrets_ref = token
        else:
            env.secrets_ref = None
    if health_check is not UNSET:
        env.health_config_json = health_check

    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project.id,
        module="environment", action="UPDATE_ENVIRONMENT",
        resource_type="environment", resource_id=str(env.id),
        summary=env.name,
        detail={"name": name, "base_url": base_url, "variable_count": len(variables) if variables else None},
    )
    return env


async def delete_environment(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    env_id: uuid.UUID,
) -> None:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    env = (
        await db.execute(
            select(Environment).where(
                Environment.id == env_id,
                Environment.project_id == project.id,
                Environment.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if env is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    env_name = env.name
    env_id_val = env.id
    await db.delete(env)
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project.id,
        module="environment", action="DELETE_ENVIRONMENT",
        resource_type="environment", resource_id=str(env_id_val),
        summary=env_name,
    )
