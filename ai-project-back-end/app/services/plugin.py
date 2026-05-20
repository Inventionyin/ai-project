from __future__ import annotations

import logging
import re
import uuid
import json
from packaging.version import Version

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.enums import PluginInstallStatus, PluginStatus, ProjectRole
from app.models.plugin import Plugin, PluginInstallation
from app.models.project import Project, ProjectMember
from app.models.audit import AuditLog
from app.schemas.plugin import PluginDetail, PluginInstallationDetail, PluginInvokeRecordDetail, PluginInvokeResponse, SandboxPolicy
from app.services.platform_record import create_audit_log
from app.services.plugin_sandbox import run_plugin_sandbox

logger = logging.getLogger(__name__)

_PLATFORM_VERSION = "1.0.0"
_ALLOWED_PERMISSIONS = {"RUN_TEST", "READ_PROJECT", "WRITE_REPORT", "CALL_EXTERNAL"}
_ALLOWED_NETWORK_MODES = {"OFF", "ALLOWLIST"}
_HOSTNAME_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*$")
_DEFAULT_SANDBOX_POLICY = {
    "permissions": ["RUN_TEST", "READ_PROJECT", "WRITE_REPORT"],
    "timeoutMs": 30000,
    "networkMode": "OFF",
    "allowedHosts": [],
    "maxPayloadBytes": 65536,
}


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


def _check_version_compatibility(min_platform_version: str | None) -> bool:
    if not min_platform_version:
        return True
    try:
        return Version(_PLATFORM_VERSION) >= Version(min_platform_version)
    except Exception:
        return True


def _json_size_bytes(value: dict | None) -> int:
    if value is None:
        return 0
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _is_valid_hostname(host: str) -> bool:
    return bool(_HOSTNAME_RE.fullmatch(host))


def _normalize_sandbox_policy(config: dict | None, *, context: str) -> dict:
    config_obj = dict(config or {})
    raw_policy = config_obj.get("sandboxPolicy")
    if raw_policy is None:
        raw_policy = {}
    if not isinstance(raw_policy, dict):
        raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy must be an object")

    merged = dict(_DEFAULT_SANDBOX_POLICY)
    merged.update(raw_policy)

    permissions = merged.get("permissions")
    if not isinstance(permissions, list) or any(not isinstance(p, str) for p in permissions):
        raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy.permissions must be a string list")
    invalid_permissions = [p for p in permissions if p not in _ALLOWED_PERMISSIONS]
    if invalid_permissions:
        raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy.permissions contains invalid values")

    timeout_ms = merged.get("timeoutMs")
    if not isinstance(timeout_ms, int) or not (100 <= timeout_ms <= 120000):
        raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy.timeoutMs must be 100..120000")

    max_payload_bytes = merged.get("maxPayloadBytes")
    if not isinstance(max_payload_bytes, int) or not (1024 <= max_payload_bytes <= 1048576):
        raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy.maxPayloadBytes must be 1024..1048576")

    network_mode = merged.get("networkMode")
    if network_mode not in _ALLOWED_NETWORK_MODES:
        raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy.networkMode must be OFF or ALLOWLIST")

    allowed_hosts = merged.get("allowedHosts")
    if not isinstance(allowed_hosts, list) or any(not isinstance(h, str) for h in allowed_hosts):
        raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy.allowedHosts must be a string list")
    if network_mode == "OFF" and allowed_hosts:
        raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy.allowedHosts must be empty when networkMode=OFF")
    if network_mode == "ALLOWLIST":
        if not allowed_hosts:
            raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy.allowedHosts required when networkMode=ALLOWLIST")
        if any(not _is_valid_hostname(h) for h in allowed_hosts):
            raise HTTPException(status_code=400, detail=f"{context} sandboxPolicy.allowedHosts contains invalid hostname")

    normalized_policy = {
        "permissions": permissions,
        "timeoutMs": timeout_ms,
        "networkMode": network_mode,
        "allowedHosts": allowed_hosts,
        "maxPayloadBytes": max_payload_bytes,
    }
    config_obj["sandboxPolicy"] = normalized_policy
    return config_obj


def _sandbox_policy_from_config(config: dict | None) -> SandboxPolicy:
    normalized = _normalize_sandbox_policy(config, context="Plugin config")
    return SandboxPolicy.model_validate(normalized["sandboxPolicy"])


def _to_plugin_detail(row: Plugin) -> PluginDetail:
    config_schema = dict(row.config_schema_json) if row.config_schema_json else None
    return PluginDetail(
        id=str(row.id),
        name=row.name,
        slug=row.slug,
        description=row.description,
        version=row.version,
        author=row.author,
        pluginType=row.plugin_type,
        configSchema=config_schema,
        entryPoint=row.entry_point,
        minPlatformVersion=row.min_platform_version,
        iconUrl=row.icon_url,
        enabled=row.enabled,
        status=row.status,
        downloadCount=row.download_count,
        createdAt=int(row.created_at.timestamp()),
        updatedAt=int(row.updated_at.timestamp()),
        sandboxPolicy=_sandbox_policy_from_config(config_schema),
    )


def _to_install_detail(row: PluginInstallation, plugin: Plugin | None = None) -> PluginInstallationDetail:
    config = dict(row.config_json) if row.config_json else None
    return PluginInstallationDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        pluginId=str(row.plugin_id),
        pluginName=plugin.name if plugin else None,
        pluginSlug=plugin.slug if plugin else None,
        status=row.status,
        config=config,
        installedVersion=row.installed_version,
        errorMessage=row.error_message,
        installedBy=str(row.installed_by) if row.installed_by else None,
        createdAt=int(row.created_at.timestamp()),
        updatedAt=int(row.updated_at.timestamp()),
        sandboxPolicy=_sandbox_policy_from_config(config),
    )


async def resolve_enabled_plugin_installation(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    plugin_slug: str | None = None,
    plugin_id: uuid.UUID | None = None,
) -> tuple[PluginInstallation, Plugin]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    if plugin_id is None and not plugin_slug:
        raise HTTPException(status_code=400, detail="plugin_slug or plugin_id is required")

    stmt = (
        select(PluginInstallation, Plugin)
        .join(Plugin, Plugin.id == PluginInstallation.plugin_id)
        .where(
            PluginInstallation.tenant_id == user.tenant_id,
            PluginInstallation.project_id == project_id,
            Plugin.tenant_id == user.tenant_id,
        )
    )
    if plugin_id is not None:
        stmt = stmt.where(Plugin.id == plugin_id)
    else:
        stmt = stmt.where(Plugin.slug == plugin_slug)

    row = (await db.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Plugin installation not found")

    installation, plugin = row
    if installation.status == PluginInstallStatus.UNINSTALLED.value:
        raise HTTPException(status_code=400, detail="Plugin is uninstalled")
    if installation.status != PluginInstallStatus.INSTALLED.value:
        raise HTTPException(status_code=400, detail=f"Plugin installation is not ready: {installation.status}")
    if not plugin.enabled:
        raise HTTPException(status_code=400, detail="Plugin is disabled")
    if plugin.status not in (
        PluginStatus.AVAILABLE.value,
        PluginStatus.INSTALLED.value,
        PluginStatus.ENABLED.value,
    ):
        raise HTTPException(status_code=400, detail=f"Plugin status is not callable: {plugin.status}")
    return installation, plugin


async def create_plugin(
    db: AsyncSession, *, user: CurrentUser,
    name: str, slug: str, version: str, description: str | None = None,
    author: str | None = None, plugin_type: str = "executor",
    config_schema: dict | None = None, entry_point: str | None = None,
    min_platform_version: str | None = None, icon_url: str | None = None,
) -> PluginDetail:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Only admin can create plugins")
    existing = await db.scalar(select(Plugin).where(
        Plugin.tenant_id == user.tenant_id, Plugin.slug == slug,
    ))
    if existing:
        raise HTTPException(status_code=409, detail="Plugin with this slug already exists")
    if not _check_version_compatibility(min_platform_version):
        raise HTTPException(status_code=400, detail=f"Plugin requires platform version >= {min_platform_version}")
    normalized_config_schema = _normalize_sandbox_policy(config_schema, context="Plugin config")
    row = Plugin(
        tenant_id=user.tenant_id, name=name, slug=slug, version=version,
        description=description, author=author, plugin_type=plugin_type,
        config_schema_json=normalized_config_schema, entry_point=entry_point,
        min_platform_version=min_platform_version, icon_url=icon_url,
        created_by=user.id,
    )
    db.add(row)
    await db.flush()
    return _to_plugin_detail(row)


async def list_plugins(
    db: AsyncSession, *, user: CurrentUser,
    page: int, page_size: int,
) -> tuple[int, list[PluginDetail]]:
    base = select(Plugin).where(Plugin.tenant_id == user.tenant_id)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(base.order_by(desc(Plugin.created_at)).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return total, [_to_plugin_detail(r) for r in rows]


async def get_plugin(
    db: AsyncSession, *, user: CurrentUser, plugin_id: uuid.UUID,
) -> PluginDetail:
    row = await db.scalar(select(Plugin).where(
        Plugin.id == plugin_id, Plugin.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return _to_plugin_detail(row)


async def update_plugin(
    db: AsyncSession, *, user: CurrentUser, plugin_id: uuid.UUID, **kwargs,
) -> PluginDetail:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Only admin can update plugins")
    row = await db.scalar(select(Plugin).where(
        Plugin.id == plugin_id, Plugin.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    for key, value in kwargs.items():
        if value is not None:
            if key == "name":
                row.name = value
            elif key == "description":
                row.description = value
            elif key == "version":
                row.version = value
            elif key == "config_schema":
                row.config_schema_json = _normalize_sandbox_policy(value, context="Plugin config")
            elif key == "entry_point":
                row.entry_point = value
            elif key == "enabled":
                row.enabled = value
            elif key == "icon_url":
                row.icon_url = value
    await db.flush()
    return _to_plugin_detail(row)


async def delete_plugin(
    db: AsyncSession, *, user: CurrentUser, plugin_id: uuid.UUID,
) -> None:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Only admin can delete plugins")
    row = await db.scalar(select(Plugin).where(
        Plugin.id == plugin_id, Plugin.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    installs = (await db.execute(select(PluginInstallation).where(
        PluginInstallation.plugin_id == plugin_id,
        PluginInstallation.status.in_([PluginInstallStatus.INSTALLED.value, PluginInstallStatus.INSTALLING.value]),
    ))).scalars().all()
    if installs:
        raise HTTPException(status_code=400, detail="Plugin has active installations, uninstall first")
    await db.delete(row)
    await db.flush()


async def install_plugin(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    plugin_id: uuid.UUID, config: dict | None = None,
) -> PluginInstallationDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    plugin = await db.scalar(select(Plugin).where(
        Plugin.id == plugin_id, Plugin.tenant_id == user.tenant_id,
    ))
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    if not _check_version_compatibility(plugin.min_platform_version):
        raise HTTPException(status_code=400, detail=f"Plugin requires platform version >= {plugin.min_platform_version}")
    existing = await db.scalar(select(PluginInstallation).where(
        PluginInstallation.project_id == project_id,
        PluginInstallation.plugin_id == plugin_id,
        PluginInstallation.status.in_([PluginInstallStatus.INSTALLED.value, PluginInstallStatus.INSTALLING.value]),
    ))
    if existing:
        raise HTTPException(status_code=409, detail="Plugin already installed in this project")
    normalized_config = _normalize_sandbox_policy(config, context="Installation config")
    policy = normalized_config["sandboxPolicy"]
    if _json_size_bytes(normalized_config) > int(policy["maxPayloadBytes"]):
        raise HTTPException(status_code=400, detail="Installation config exceeds sandboxPolicy.maxPayloadBytes")
    row = PluginInstallation(
        tenant_id=user.tenant_id, project_id=project_id, plugin_id=plugin_id,
        status=PluginInstallStatus.INSTALLED.value,
        config_json=normalized_config, installed_version=plugin.version,
        installed_by=user.id,
    )
    db.add(row)
    plugin.download_count += 1
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        action="INSTALL_PLUGIN", resource_type="plugin_installation",
        resource_id=str(row.id), summary=f"安装插件: {plugin.name}",
    )
    return _to_install_detail(row, plugin)


async def uninstall_plugin(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, installation_id: uuid.UUID,
) -> None:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(select(PluginInstallation).where(
        PluginInstallation.id == installation_id,
        PluginInstallation.project_id == project_id,
        PluginInstallation.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Installation not found")
    row.status = PluginInstallStatus.UNINSTALLED.value
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        action="UNINSTALL_PLUGIN", resource_type="plugin_installation",
        resource_id=str(row.id), summary="卸载插件",
    )


async def toggle_plugin(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    installation_id: uuid.UUID, enabled: bool,
) -> PluginInstallationDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(select(PluginInstallation).where(
        PluginInstallation.id == installation_id,
        PluginInstallation.project_id == project_id,
        PluginInstallation.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Installation not found")
    if row.status != PluginInstallStatus.INSTALLED.value:
        raise HTTPException(status_code=400, detail="Can only toggle installed plugins")
    plugin = await db.scalar(select(Plugin).where(Plugin.id == row.plugin_id))
    if plugin:
        plugin.enabled = enabled
    await db.flush()
    action = "ENABLE_PLUGIN" if enabled else "DISABLE_PLUGIN"
    await create_audit_log(
        db, user=user, project_id=project_id,
        action=action, resource_type="plugin_installation",
        resource_id=str(row.id), summary=f"{'启用' if enabled else '停用'}插件",
    )
    return _to_install_detail(row, plugin)


async def list_installations(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    page: int, page_size: int,
) -> tuple[int, list[PluginInstallationDetail]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base = select(PluginInstallation).where(
        PluginInstallation.tenant_id == user.tenant_id,
        PluginInstallation.project_id == project_id,
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(
        base.order_by(desc(PluginInstallation.created_at)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    items = []
    for r in rows:
        plugin = await db.scalar(select(Plugin).where(Plugin.id == r.plugin_id))
        items.append(_to_install_detail(r, plugin))
    return total, items


async def invoke_plugin_installation(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    installation_id: uuid.UUID,
    payload: dict | None = None,
) -> PluginInvokeResponse:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    row = await db.scalar(select(PluginInstallation).where(
        PluginInstallation.id == installation_id,
        PluginInstallation.project_id == project_id,
        PluginInstallation.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Installation not found")

    installation, plugin = await resolve_enabled_plugin_installation(
        db,
        user=user,
        project_id=project_id,
        plugin_id=row.plugin_id,
    )
    normalized_config = _normalize_sandbox_policy(
        dict(installation.config_json) if installation.config_json else None,
        context="Installation config",
    )
    policy = normalized_config["sandboxPolicy"]
    if _json_size_bytes(payload) > int(policy["maxPayloadBytes"]):
        raise HTTPException(status_code=400, detail="Invocation payload exceeds sandboxPolicy.maxPayloadBytes")
    execution = None
    status = "accepted"
    if plugin.entry_point:
        execution = await run_plugin_sandbox(
            plugin_slug=plugin.slug,
            entry_point=plugin.entry_point,
            payload=payload,
            sandbox_policy=policy,
        )
        status = execution.status
    result = PluginInvokeResponse(
        installationId=str(installation.id),
        pluginId=str(plugin.id),
        pluginSlug=plugin.slug,
        status=status,
        sandboxPolicy=SandboxPolicy.model_validate(policy),
        executionId=execution.execution_id if execution else None,
        exitCode=execution.exit_code if execution else None,
        durationMs=execution.duration_ms if execution else None,
        timedOut=execution.timed_out if execution else False,
        output=execution.output if execution else None,
        error=execution.error if execution else None,
    )
    await create_audit_log(
        db,
        user=user,
        project_id=project_id,
        module="plugin",
        action="INVOKE_PLUGIN",
        resource_type="plugin_installation",
        resource_id=str(installation.id),
        summary=f"调用插件: {plugin.slug}",
        detail={
            "project_id": str(project_id),
            "plugin_id": str(plugin.id),
            "plugin_slug": plugin.slug,
            "installation_id": str(installation.id),
            "invoked_by": str(user.id),
            "status": result.status,
            "sandbox_policy": policy,
            "payload_bytes": _json_size_bytes(payload),
            "execution": {
                "execution_id": execution.execution_id,
                "status": execution.status,
                "exit_code": execution.exit_code,
                "duration_ms": execution.duration_ms,
                "timed_out": execution.timed_out,
                "error": execution.error,
            } if execution else None,
        },
    )
    return result


async def list_plugin_invocations(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    installation_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[int, list[PluginInvokeRecordDetail]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    installation = await db.scalar(select(PluginInstallation).where(
        PluginInstallation.id == installation_id,
        PluginInstallation.project_id == project_id,
        PluginInstallation.tenant_id == user.tenant_id,
    ))
    if installation is None:
        raise HTTPException(status_code=404, detail="Installation not found")

    base = select(AuditLog).where(
        AuditLog.tenant_id == user.tenant_id,
        AuditLog.project_id == project_id,
        AuditLog.action == "INVOKE_PLUGIN",
        AuditLog.resource_type == "plugin_installation",
        AuditLog.resource_id == str(installation_id),
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(
        base.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    items = []
    for row in rows:
        detail = dict(row.detail_json or {})
        items.append(PluginInvokeRecordDetail(
            id=str(row.id),
            installationId=str(installation_id),
            pluginId=detail.get("plugin_id"),
            pluginSlug=detail.get("plugin_slug"),
            invokedBy=detail.get("invoked_by"),
            status=str(detail.get("status") or "unknown"),
            createdAt=int(row.created_at.timestamp()),
        ))
    return total, items
