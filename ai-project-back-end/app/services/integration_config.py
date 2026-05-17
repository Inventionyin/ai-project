from __future__ import annotations

import re
import uuid

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.enums import ProjectRole
from app.models.integration import Notification, NotificationOutbox
from app.models.project import Project, ProjectMember
from app.models.prompt_template import PromptTemplate
from app.models.run import Run
from app.schemas.integration import (
    NotificationConfigCreateRequest,
    NotificationConfigDetail,
    NotificationStrategyCenterDeliveryStats,
    NotificationStrategyCenterFilterReasonStats,
    NotificationStrategyCenterItem,
    NotificationStrategyCenterSimulationStats,
    NotificationStrategyCenterSimulationScopeReasonItem,
    NotificationDeliveryListData,
    NotificationDeliveryListItem,
    NotificationDeliveryRetryResult,
    NotificationConfigUpdateRequest,
    NotificationStrategySimulationBatchItem,
    NotificationStrategySimulationBatchResult,
    NotificationStrategySimulationResult,
    NotificationStrategySimulateRunContext,
)
from app.services.integration_delivery import process_notification_outbox_item, simulate_rollout_scope
from app.services.platform_record import create_audit_log

_ALLOWED_EVENTS = {"RUN_PASSED", "RUN_FAILED", "RUN_CANCELED", "RUN_FINISHED"}
_ALLOWED_TEMPLATE_VARS = {"runId", "status", "projectName", "passRate", "failCount", "reportUrl"}
_ALLOWED_TRIGGER_TYPES = {"MANUAL", "CRON", "CI", "WEBHOOK"}
_TEMPLATE_VAR_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")
_DEFAULT_TEMPLATE_SCENE_BY_CHANNEL = {
    "WEBHOOK": "NOTIFICATION_WEBHOOK",
    "EMAIL": "NOTIFICATION_EMAIL",
    "IM": "NOTIFICATION_IM",
}
_ALLOWED_TEMPLATE_SCENES = frozenset(_DEFAULT_TEMPLATE_SCENE_BY_CHANNEL.values())
_LAYER_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_ACTION_CREATE_NOTIFICATION_RULE = "CREATE_NOTIFICATION_RULE"
_ACTION_UPDATE_NOTIFICATION_RULE = "UPDATE_NOTIFICATION_RULE"
_ACTION_DELETE_NOTIFICATION_RULE = "DELETE_NOTIFICATION_RULE"


def _default_template_scene(channel: str) -> str:
    return _DEFAULT_TEMPLATE_SCENE_BY_CHANNEL.get(channel.upper(), "NOTIFICATION_WEBHOOK")


def _normalize_template_scene(channel: str, value: object | None) -> str:
    default_scene = _default_template_scene(channel)
    raw = str(value or "").strip().upper()
    if not raw:
        return default_scene
    # backward compatibility: legacy scene aliases used channel names directly
    if raw in _DEFAULT_TEMPLATE_SCENE_BY_CHANNEL:
        return _DEFAULT_TEMPLATE_SCENE_BY_CHANNEL[raw]
    return raw


def _bad_rule(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=message)


def _validate_time_window_object(*, time_window: dict[str, object], path_prefix: str) -> None:
    timezone_offset = time_window.get("timezoneOffsetMinutes")
    if timezone_offset is not None:
        if isinstance(timezone_offset, bool) or not isinstance(timezone_offset, int):
            raise _bad_rule(f"{path_prefix}.timezoneOffsetMinutes must be an integer between -720 and 840")
        if timezone_offset < -720 or timezone_offset > 840:
            raise _bad_rule(f"{path_prefix}.timezoneOffsetMinutes must be an integer between -720 and 840")

    weekdays = time_window.get("weekdays")
    if weekdays is not None:
        if not isinstance(weekdays, list) or len(weekdays) == 0:
            raise _bad_rule(f"{path_prefix}.weekdays must be an array with values 1..7")
        normalized_weekdays: list[int] = []
        seen_weekdays: set[int] = set()
        for item in weekdays:
            if isinstance(item, bool) or not isinstance(item, int):
                raise _bad_rule(f"{path_prefix}.weekdays must be an array with values 1..7")
            if item < 1 or item > 7:
                raise _bad_rule(f"{path_prefix}.weekdays must be an array with values 1..7")
            if item not in seen_weekdays:
                seen_weekdays.add(item)
                normalized_weekdays.append(item)
        time_window["weekdays"] = normalized_weekdays

    start_hour = time_window.get("startHour")
    end_hour = time_window.get("endHour")
    if start_hour is None and end_hour is not None:
        raise _bad_rule(f"{path_prefix}.startHour is required when {path_prefix}.endHour is set")
    if end_hour is None and start_hour is not None:
        raise _bad_rule(f"{path_prefix}.endHour is required when {path_prefix}.startHour is set")
    if start_hour is not None:
        if isinstance(start_hour, bool) or not isinstance(start_hour, int):
            raise _bad_rule(f"{path_prefix}.startHour must be an integer between 0 and 23")
        if start_hour < 0 or start_hour > 23:
            raise _bad_rule(f"{path_prefix}.startHour must be an integer between 0 and 23")
    if end_hour is not None:
        if isinstance(end_hour, bool) or not isinstance(end_hour, int):
            raise _bad_rule(f"{path_prefix}.endHour must be an integer between 0 and 23")
        if end_hour < 0 or end_hour > 23:
            raise _bad_rule(f"{path_prefix}.endHour must be an integer between 0 and 23")


def _validate_rule_json(*, channel: str, rule: dict[str, object]) -> None:
    events = rule.get("events")
    if events is not None:
        if not isinstance(events, list) or len(events) == 0:
            raise _bad_rule("rule.events must be a non-empty array of allowed event names")
        if any(not isinstance(item, str) or item not in _ALLOWED_EVENTS for item in events):
            raise _bad_rule("rule.events contains invalid event")

    template = rule.get("template")
    if template is not None:
        if not isinstance(template, str):
            raise _bad_rule("rule.template must be a string")
        used_vars = set(_TEMPLATE_VAR_PATTERN.findall(template))
        invalid_vars = sorted(var for var in used_vars if var not in _ALLOWED_TEMPLATE_VARS)
        if invalid_vars:
            raise _bad_rule(f"rule.template contains invalid variable(s): {', '.join(invalid_vars)}")

    template_name = rule.get("templateName")
    if template_name is not None:
        if not isinstance(template_name, str):
            raise _bad_rule("rule.templateName must be a string")
        if not template_name.strip():
            raise _bad_rule("rule.templateName must not be empty")
        if len(template_name.strip()) > 128:
            raise _bad_rule("rule.templateName length must be <= 128")

    template_version = rule.get("templateVersion")
    if template_version is not None:
        if not isinstance(template_version, str):
            raise _bad_rule("rule.templateVersion must be a string")
        if not template_version.strip():
            raise _bad_rule("rule.templateVersion must not be empty")
        if len(template_version.strip()) > 32:
            raise _bad_rule("rule.templateVersion length must be <= 32")

    template_scene = rule.get("templateScene")
    if template_scene is not None:
        if not isinstance(template_scene, str):
            raise _bad_rule("rule.templateScene must be a string")
        if not template_scene.strip():
            raise _bad_rule("rule.templateScene must not be empty")
        normalized_scene = _normalize_template_scene(channel, template_scene)
        if normalized_scene not in _ALLOWED_TEMPLATE_SCENES:
            raise _bad_rule(
                "rule.templateScene must be one of NOTIFICATION_WEBHOOK, NOTIFICATION_EMAIL, NOTIFICATION_IM"
            )
        rule["templateScene"] = normalized_scene

    if template_version is not None and template_name is None:
        raise _bad_rule("rule.templateVersion requires rule.templateName")

    # keep a stable default scene contract for notification template references
    if template_name is not None and template_scene is None:
        rule["templateScene"] = _default_template_scene(channel)

    timeout_sec = rule.get("timeoutSec")
    if timeout_sec is not None:
        if isinstance(timeout_sec, bool) or not isinstance(timeout_sec, int | float):
            raise _bad_rule("rule.timeoutSec must be a number between 0.1 and 30")
        timeout_sec = float(timeout_sec)
        if timeout_sec < 0.1 or timeout_sec > 30:
            raise _bad_rule("rule.timeoutSec must be a number between 0.1 and 30")

    max_retries = rule.get("maxRetries")
    if max_retries is not None:
        if isinstance(max_retries, bool) or not isinstance(max_retries, int):
            raise _bad_rule("rule.maxRetries must be an integer between 1 and 5")
        if max_retries < 1 or max_retries > 5:
            raise _bad_rule("rule.maxRetries must be an integer between 1 and 5")

    provider = rule.get("provider")
    if provider is not None:
        if channel == "WEBHOOK":
            if not isinstance(provider, str):
                raise _bad_rule("rule.provider must be a string when provided")
        elif not isinstance(provider, str):
            raise _bad_rule("rule.provider must be a string when provided")

    secret = rule.get("secret")
    if secret is not None and not isinstance(secret, str):
        raise _bad_rule("rule.secret must be a string when provided")

    template_strategy = rule.get("templateStrategy")
    if template_strategy is not None:
        if not isinstance(template_strategy, str):
            raise _bad_rule("rule.templateStrategy must be one of ACTIVE or CANARY")
        template_strategy = template_strategy.strip().upper()
        if template_strategy not in {"ACTIVE", "CANARY"}:
            raise _bad_rule("rule.templateStrategy must be one of ACTIVE or CANARY")

    template_canary_version = rule.get("templateCanaryVersion")
    if template_canary_version is not None:
        if not isinstance(template_canary_version, str):
            raise _bad_rule("rule.templateCanaryVersion must be a string")
        if not template_canary_version.strip():
            raise _bad_rule("rule.templateCanaryVersion must not be empty")

    template_canary_percent = rule.get("templateCanaryPercent")
    if template_canary_percent is not None:
        if isinstance(template_canary_percent, bool) or not isinstance(template_canary_percent, int | float):
            raise _bad_rule("rule.templateCanaryPercent must be a number between 1 and 100")
        if float(template_canary_percent) < 1 or float(template_canary_percent) > 100:
            raise _bad_rule("rule.templateCanaryPercent must be a number between 1 and 100")

    if template_strategy == "CANARY":
        if template_name is None:
            raise _bad_rule("rule.templateName is required when rule.templateStrategy is CANARY")
        if template_version is not None:
            raise _bad_rule("rule.templateVersion must not be set when rule.templateStrategy is CANARY")
        if template_canary_version is None:
            raise _bad_rule("rule.templateCanaryVersion is required when rule.templateStrategy is CANARY")
        if template_canary_percent is None:
            raise _bad_rule("rule.templateCanaryPercent is required when rule.templateStrategy is CANARY")

    auto_rollback_enabled = rule.get("autoRollbackEnabled")
    if auto_rollback_enabled is not None and not isinstance(auto_rollback_enabled, bool):
        raise _bad_rule("rule.autoRollbackEnabled must be a boolean")

    auto_rollback_failure_threshold = rule.get("autoRollbackFailureThreshold")
    if auto_rollback_failure_threshold is not None:
        if isinstance(auto_rollback_failure_threshold, bool) or not isinstance(auto_rollback_failure_threshold, int):
            raise _bad_rule("rule.autoRollbackFailureThreshold must be an integer between 1 and 20")
        if auto_rollback_failure_threshold < 1 or auto_rollback_failure_threshold > 20:
            raise _bad_rule("rule.autoRollbackFailureThreshold must be an integer between 1 and 20")

    auto_rollback_window_minutes = rule.get("autoRollbackWindowMinutes")
    if auto_rollback_window_minutes is not None:
        if isinstance(auto_rollback_window_minutes, bool) or not isinstance(auto_rollback_window_minutes, int):
            raise _bad_rule("rule.autoRollbackWindowMinutes must be an integer between 1 and 1440")
        if auto_rollback_window_minutes < 1 or auto_rollback_window_minutes > 1440:
            raise _bad_rule("rule.autoRollbackWindowMinutes must be an integer between 1 and 1440")

    rollout_scope = rule.get("rolloutScope")
    if rollout_scope is not None:
        if not isinstance(rollout_scope, dict):
            raise _bad_rule("rule.rolloutScope must be an object")

        env_ids = rollout_scope.get("envIds")
        if env_ids is not None:
            if not isinstance(env_ids, list) or any(not isinstance(item, str) for item in env_ids):
                raise _bad_rule("rule.rolloutScope.envIds must be an array of UUID strings")
            normalized_env_ids: list[str] = []
            seen_env_ids: set[str] = set()
            for item in env_ids:
                normalized = item.strip().lower()
                try:
                    uuid.UUID(normalized)
                except (ValueError, AttributeError):
                    raise _bad_rule("rule.rolloutScope.envIds must be an array of UUID strings")
                if normalized not in seen_env_ids:
                    seen_env_ids.add(normalized)
                    normalized_env_ids.append(normalized)
            rollout_scope["envIds"] = normalized_env_ids

        trigger_types = rollout_scope.get("triggerTypes")
        if trigger_types is not None:
            if not isinstance(trigger_types, list) or any(not isinstance(item, str) for item in trigger_types):
                raise _bad_rule(
                    "rule.rolloutScope.triggerTypes must be an array of MANUAL/CRON/CI/WEBHOOK"
                )
            normalized_trigger_types: list[str] = []
            seen_trigger_types: set[str] = set()
            for item in trigger_types:
                normalized = item.strip().upper()
                if normalized not in _ALLOWED_TRIGGER_TYPES:
                    raise _bad_rule(
                        "rule.rolloutScope.triggerTypes must be an array of MANUAL/CRON/CI/WEBHOOK"
                    )
                if normalized not in seen_trigger_types:
                    seen_trigger_types.add(normalized)
                    normalized_trigger_types.append(normalized)
            rollout_scope["triggerTypes"] = normalized_trigger_types

        meta_tags = rollout_scope.get("metaTags")
        if meta_tags is not None:
            if not isinstance(meta_tags, list) or any(not isinstance(item, str) for item in meta_tags):
                raise _bad_rule("rule.rolloutScope.metaTags must be an array of non-empty strings")
            normalized_meta_tags: list[str] = []
            seen_meta_tags: set[str] = set()
            for item in meta_tags:
                normalized = item.strip()
                if not normalized:
                    raise _bad_rule("rule.rolloutScope.metaTags must be an array of non-empty strings")
                if normalized not in seen_meta_tags:
                    seen_meta_tags.add(normalized)
                    normalized_meta_tags.append(normalized)
            rollout_scope["metaTags"] = normalized_meta_tags

        batch_percent = rollout_scope.get("batchPercent")
        if batch_percent is not None:
            if isinstance(batch_percent, bool) or not isinstance(batch_percent, int):
                raise _bad_rule("rule.rolloutScope.batchPercent must be an integer between 1 and 100")
            if batch_percent < 1 or batch_percent > 100:
                raise _bad_rule("rule.rolloutScope.batchPercent must be an integer between 1 and 100")

        priority = rollout_scope.get("priority")
        if priority is not None:
            if isinstance(priority, bool) or not isinstance(priority, int):
                raise _bad_rule("rule.rolloutScope.priority must be an integer between 1 and 1000")
            if priority < 1 or priority > 1000:
                raise _bad_rule("rule.rolloutScope.priority must be an integer between 1 and 1000")

        layer_key_raw = rollout_scope.get("layerKey")
        layer_values_raw = rollout_scope.get("layerValues")
        normalized_layer_key: str | None = None
        if layer_key_raw is not None:
            if not isinstance(layer_key_raw, str):
                raise _bad_rule("rule.rolloutScope.layerKey must be a string")
            normalized_layer_key = layer_key_raw.strip()
            if not normalized_layer_key:
                raise _bad_rule("rule.rolloutScope.layerKey must not be empty")
            if not _LAYER_KEY_PATTERN.match(normalized_layer_key):
                raise _bad_rule("rule.rolloutScope.layerKey must match ^[A-Za-z][A-Za-z0-9_]{0,63}$")
            rollout_scope["layerKey"] = normalized_layer_key

        if layer_values_raw is not None:
            if not isinstance(layer_values_raw, list) or any(not isinstance(item, str) for item in layer_values_raw):
                raise _bad_rule("rule.rolloutScope.layerValues must be an array of non-empty strings")
            normalized_layer_values: list[str] = []
            seen_layer_values: set[str] = set()
            for item in layer_values_raw:
                normalized = item.strip()
                if not normalized:
                    raise _bad_rule("rule.rolloutScope.layerValues must be an array of non-empty strings")
                key = normalized.lower()
                if key in seen_layer_values:
                    continue
                seen_layer_values.add(key)
                normalized_layer_values.append(normalized)
            if not normalized_layer_values:
                raise _bad_rule("rule.rolloutScope.layerValues must contain at least one value")
            rollout_scope["layerValues"] = normalized_layer_values

        if normalized_layer_key is not None and not isinstance(rollout_scope.get("layerValues"), list):
            raise _bad_rule("rule.rolloutScope.layerValues is required when rule.rolloutScope.layerKey is set")
        if normalized_layer_key is None and layer_values_raw is not None:
            raise _bad_rule("rule.rolloutScope.layerKey is required when rule.rolloutScope.layerValues is set")

        time_window = rollout_scope.get("timeWindow")
        if time_window is not None:
            if not isinstance(time_window, dict):
                raise _bad_rule("rule.rolloutScope.timeWindow must be an object")
            _validate_time_window_object(
                time_window=time_window,
                path_prefix="rule.rolloutScope.timeWindow",
            )

        time_windows = rollout_scope.get("timeWindows")
        if time_windows is not None:
            if not isinstance(time_windows, list):
                raise _bad_rule("rule.rolloutScope.timeWindows must be an array")
            normalized_time_windows: list[dict[str, object]] = []
            for idx, window in enumerate(time_windows):
                if not isinstance(window, dict):
                    raise _bad_rule("rule.rolloutScope.timeWindows must be an array of objects")
                normalized_window = dict(window)

                window_id = normalized_window.get("id")
                if window_id is not None:
                    if not isinstance(window_id, str):
                        raise _bad_rule("rule.rolloutScope.timeWindows.id must be a non-empty string")
                    normalized_id = window_id.strip()
                    if not normalized_id:
                        raise _bad_rule("rule.rolloutScope.timeWindows.id must be a non-empty string")
                    normalized_window["id"] = normalized_id

                enabled = normalized_window.get("enabled")
                if enabled is None:
                    normalized_window["enabled"] = True
                elif not isinstance(enabled, bool):
                    raise _bad_rule("rule.rolloutScope.timeWindows.enabled must be a boolean")

                priority_value = normalized_window.get("priority")
                if isinstance(priority_value, bool) or not isinstance(priority_value, int):
                    raise _bad_rule("rule.rolloutScope.timeWindows.priority must be an integer between 1 and 1000")
                if priority_value < 1 or priority_value > 1000:
                    raise _bad_rule("rule.rolloutScope.timeWindows.priority must be an integer between 1 and 1000")

                weight_value = normalized_window.get("weight")
                if isinstance(weight_value, bool) or not isinstance(weight_value, int):
                    raise _bad_rule("rule.rolloutScope.timeWindows.weight must be an integer between 1 and 100")
                if weight_value < 1 or weight_value > 100:
                    raise _bad_rule("rule.rolloutScope.timeWindows.weight must be an integer between 1 and 100")

                window_batch_percent = normalized_window.get("batchPercent")
                if window_batch_percent is not None:
                    if isinstance(window_batch_percent, bool) or not isinstance(window_batch_percent, int):
                        raise _bad_rule(
                            "rule.rolloutScope.timeWindows.batchPercent must be an integer between 1 and 100"
                        )
                    if window_batch_percent < 1 or window_batch_percent > 100:
                        raise _bad_rule(
                            "rule.rolloutScope.timeWindows.batchPercent must be an integer between 1 and 100"
                        )

                nested_time_window = normalized_window.get("timeWindow")
                if not isinstance(nested_time_window, dict):
                    raise _bad_rule("rule.rolloutScope.timeWindows.timeWindow must be an object")
                _validate_time_window_object(
                    time_window=nested_time_window,
                    path_prefix=f"rule.rolloutScope.timeWindows[{idx}].timeWindow",
                )
                normalized_window["timeWindow"] = nested_time_window
                normalized_time_windows.append(normalized_window)
            rollout_scope["timeWindows"] = normalized_time_windows


async def _validate_template_reference(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    channel: str,
    rule: dict[str, object],
) -> None:
    template_name_raw = rule.get("templateName")
    if template_name_raw is None:
        return

    template_name = str(template_name_raw).strip()
    if not template_name:
        return

    template_scene = _normalize_template_scene(channel, rule.get("templateScene"))
    template_version_raw = rule.get("templateVersion")

    stmt = select(PromptTemplate.id).where(
        PromptTemplate.tenant_id == user.tenant_id,
        PromptTemplate.project_id == project_id,
        PromptTemplate.scene == template_scene,
        PromptTemplate.name == template_name,
    )

    if template_version_raw is not None:
        template_version = str(template_version_raw).strip()
        row_id = await db.scalar(stmt.where(PromptTemplate.version == template_version))
        if row_id is None:
            raise _bad_rule(
                "Referenced prompt template not found for "
                f"templateScene={template_scene}, templateName={template_name}, templateVersion={template_version}"
            )
        return

    row_id = await db.scalar(stmt.where(PromptTemplate.is_active.is_(True)))
    if row_id is None:
        raise _bad_rule(
            "Active prompt template not found for "
            f"templateScene={template_scene}, templateName={template_name}"
        )


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


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


def _to_notification_detail(row: Notification) -> NotificationConfigDetail:
    return NotificationConfigDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        channel=row.channel,
        target=row.target,
        rule=dict(row.rule_json or {}),
        enabled=bool(row.enabled),
        createdAt=to_unix_ts(row.created_at),
    )


async def _get_notification_or_404(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> Notification:
    row = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.project_id == project_id,
            Notification.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return row


async def create_notification_config(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: NotificationConfigCreateRequest,
) -> NotificationConfigDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    _validate_rule_json(channel=payload.channel, rule=payload.rule)
    await _validate_template_reference(
        db,
        user=user,
        project_id=project.id,
        channel=payload.channel,
        rule=payload.rule,
    )

    row = Notification(
        tenant_id=user.tenant_id,
        project_id=project.id,
        channel=payload.channel,
        target=payload.target,
        rule_json=payload.rule,
        enabled=payload.enabled,
    )
    db.add(row)
    await db.flush()
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="INTEGRATION",
        action=_ACTION_CREATE_NOTIFICATION_RULE,
        resource_type="notification_rule",
        resource_id=str(row.id),
        summary=f"Create notification rule: {row.channel} {row.target}",
        detail={
            "channel": row.channel,
            "target": row.target,
            "enabled": bool(row.enabled),
            "events": list((row.rule_json or {}).get("events") or []),
            "rule": dict(row.rule_json or {}),
        },
    )
    return _to_notification_detail(row)


async def list_notification_configs(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[NotificationConfigDetail]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    rows = (
        await db.execute(
            select(Notification)
            .where(
                Notification.tenant_id == user.tenant_id,
                Notification.project_id == project.id,
            )
            .order_by(desc(Notification.created_at), desc(Notification.id))
        )
    ).scalars().all()
    return [_to_notification_detail(row) for row in rows]


async def update_notification_config(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    notification_id: uuid.UUID,
    payload: NotificationConfigUpdateRequest,
) -> NotificationConfigDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    _validate_rule_json(channel=payload.channel, rule=payload.rule)
    await _validate_template_reference(
        db,
        user=user,
        project_id=project.id,
        channel=payload.channel,
        rule=payload.rule,
    )
    row = await _get_notification_or_404(db, user=user, project_id=project.id, notification_id=notification_id)

    row.channel = payload.channel
    row.target = payload.target
    row.rule_json = payload.rule
    row.enabled = payload.enabled

    await db.flush()
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="INTEGRATION",
        action=_ACTION_UPDATE_NOTIFICATION_RULE,
        resource_type="notification_rule",
        resource_id=str(row.id),
        summary=f"Update notification rule: {row.channel} {row.target}",
        detail={
            "channel": row.channel,
            "target": row.target,
            "enabled": bool(row.enabled),
            "events": list((row.rule_json or {}).get("events") or []),
            "rule": dict(row.rule_json or {}),
        },
    )
    return _to_notification_detail(row)


async def delete_notification_config(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> None:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await _get_notification_or_404(db, user=user, project_id=project.id, notification_id=notification_id)
    await create_audit_log(
        db,
        user=user,
        project_id=project.id,
        module="INTEGRATION",
        action=_ACTION_DELETE_NOTIFICATION_RULE,
        resource_type="notification_rule",
        resource_id=str(row.id),
        summary=f"Delete notification rule: {row.channel} {row.target}",
        detail={
            "channel": row.channel,
            "target": row.target,
            "enabled": bool(row.enabled),
            "events": list((row.rule_json or {}).get("events") or []),
            "rule": dict(row.rule_json or {}),
        },
    )
    await db.delete(row)
    await db.flush()


def _count_scope_filtered(dispatch_results: list[object]) -> int:
    total = 0
    for item in dispatch_results:
        if isinstance(item, dict) and item.get("reason") == "scope_filtered":
            total += 1
    return total


def _count_reason(dispatch_results: list[object], reason: str) -> int:
    total = 0
    for item in dispatch_results:
        if isinstance(item, dict) and str(item.get("reason") or "") == reason:
            total += 1
    return total


def _is_scope_reason(reason: str) -> bool:
    return reason.startswith("scope_")


def _build_simulation_stats(dispatch_results: list[dict[str, object]]) -> NotificationStrategyCenterSimulationStats | None:
    if not dispatch_results:
        return None

    sample_count = len(dispatch_results)
    matched_count = 0
    scope_reason_counter: dict[str, int] = {}

    for item in dispatch_results:
        reason = str(item.get("reason") or "").strip()
        if reason and _is_scope_reason(reason):
            scope_reason_counter[reason] = int(scope_reason_counter.get(reason, 0)) + 1
        else:
            matched_count += 1

    top_scope_reasons = sorted(scope_reason_counter.items(), key=lambda pair: (-pair[1], pair[0]))[:3]

    return NotificationStrategyCenterSimulationStats(
        sampleCount=sample_count,
        matchedCount=matched_count,
        scopeReasonTop=[
            NotificationStrategyCenterSimulationScopeReasonItem(reason=reason, count=count)
            for reason, count in top_scope_reasons
        ],
    )


async def list_notification_strategy_center(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[NotificationStrategyCenterItem]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    notifications = (
        await db.execute(
            select(Notification)
            .where(
                Notification.tenant_id == user.tenant_id,
                Notification.project_id == project.id,
            )
            .order_by(desc(Notification.created_at), desc(Notification.id))
        )
    ).scalars().all()
    outbox_rows = (
        await db.execute(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.tenant_id == user.tenant_id,
                NotificationOutbox.project_id == project.id,
            )
            .order_by(desc(NotificationOutbox.created_at), desc(NotificationOutbox.id))
        )
    ).scalars().all()

    outbox_map: dict[uuid.UUID, list[NotificationOutbox]] = {}
    for row in outbox_rows:
        outbox_map.setdefault(row.notification_id, []).append(row)
    runs = (
        await db.execute(
            select(Run.summary_json).where(
                Run.tenant_id == user.tenant_id,
                Run.project_id == project.id,
            )
        )
    ).all()
    dispatch_result_map: dict[str, list[dict[str, object]]] = {}
    for (summary_json,) in runs:
        summary = dict(summary_json or {})
        dispatch = dict(summary.get("notificationDispatch") or {})
        terminal = dict(dispatch.get("terminal") or {})
        results = terminal.get("results")
        if not isinstance(results, list):
            continue
        for item in results:
            if not isinstance(item, dict):
                continue
            notification_id = str(item.get("notificationId") or "").strip()
            if not notification_id:
                continue
            dispatch_result_map.setdefault(notification_id, []).append(item)

    items: list[NotificationStrategyCenterItem] = []
    for row in notifications:
        rule = dict(row.rule_json or {})
        events = [str(item).strip().upper() for item in (rule.get("events") or []) if str(item).strip()]

        template_summary = {
            "mode": str(rule.get("templateStrategy") or "ACTIVE").strip().upper(),
            "templateName": rule.get("templateName"),
            "templateScene": rule.get("templateScene"),
            "templateVersion": rule.get("templateVersion"),
            "templateCanaryVersion": rule.get("templateCanaryVersion"),
            "templateCanaryPercent": rule.get("templateCanaryPercent"),
            "hasInlineTemplate": bool(str(rule.get("template") or "").strip()),
        }
        rollout_scope = dict(rule.get("rolloutScope") or {})
        time_window = dict(rollout_scope.get("timeWindow") or {})
        time_windows_raw = rollout_scope.get("timeWindows")
        time_windows_list = [item for item in time_windows_raw if isinstance(item, dict)] if isinstance(time_windows_raw, list) else []
        time_windows_enabled = 0
        for window in time_windows_list:
            enabled = window.get("enabled")
            if not isinstance(enabled, bool) or enabled:
                time_windows_enabled += 1
        rollout_scope_summary = {
            "envIdsCount": len(rollout_scope.get("envIds") or []),
            "triggerTypes": list(rollout_scope.get("triggerTypes") or []),
            "metaTagsCount": len(rollout_scope.get("metaTags") or []),
            "batchPercent": rollout_scope.get("batchPercent"),
            "priority": rollout_scope.get("priority"),
            "layerKey": rollout_scope.get("layerKey"),
            "layerValuesCount": len(rollout_scope.get("layerValues") or []),
            "timeWindow": {
                "timezoneOffsetMinutes": time_window.get("timezoneOffsetMinutes"),
                "weekdays": list(time_window.get("weekdays") or []),
                "startHour": time_window.get("startHour"),
                "endHour": time_window.get("endHour"),
            },
            "timeWindows": {
                "total": len(time_windows_list),
                "enabled": time_windows_enabled,
                "conflictStrategy": "priority_asc_then_weight_desc_then_array_order",
            },
        }
        auto_rollback_summary = {
            "enabled": bool(rule.get("autoRollbackEnabled")),
            "failureThreshold": rule.get("autoRollbackFailureThreshold"),
            "windowMinutes": rule.get("autoRollbackWindowMinutes"),
        }

        outbox_list = outbox_map.get(row.id, [])
        sent = 0
        failed = 0
        queued = 0
        last_delivery_at = None
        last_status = None
        if outbox_list:
            for outbox in outbox_list:
                status = str(outbox.status or "").upper()
                if status == "SENT":
                    sent += 1
                elif status == "FAILED":
                    failed += 1
                elif status == "QUEUED":
                    queued += 1
            latest = max(outbox_list, key=lambda item: ((item.updated_at or item.created_at), item.id))
            last_delivery_at = to_unix_ts(latest.updated_at or latest.created_at)
            last_status = str(latest.status or "").upper() or None

        dispatch_results = dispatch_result_map.get(str(row.id), [])
        simulation_stats = _build_simulation_stats(dispatch_results)
        scope_reason_count = _count_scope_filtered(dispatch_results)
        event_filtered_count = _count_reason(dispatch_results, "event_filtered")
        unsupported_provider_count = _count_reason(dispatch_results, "unsupported_provider")
        template_not_found_count = 0
        for item in dispatch_results:
            if isinstance(item, dict) and str(item.get("templateReason") or "") == "template_not_found":
                template_not_found_count += 1

        items.append(
            NotificationStrategyCenterItem(
                id=str(row.id),
                channel=str(row.channel),
                target=str(row.target),
                enabled=bool(row.enabled),
                events=events,
                templateStrategySummary=template_summary,
                rolloutScopeSummary=rollout_scope_summary,
                autoRollbackSummary=auto_rollback_summary,
                deliveryStats=NotificationStrategyCenterDeliveryStats(
                    sent=sent,
                    failed=failed,
                    queued=queued,
                    lastDeliveryAt=last_delivery_at,
                    lastStatus=last_status,
                ),
                filterReasonStats=NotificationStrategyCenterFilterReasonStats(
                    scopeReason=scope_reason_count,
                    eventFiltered=event_filtered_count,
                    unsupportedProvider=unsupported_provider_count,
                    templateNotFound=template_not_found_count,
                ),
                simulationStats=simulation_stats,
            )
        )
    return items


async def simulate_notification_strategy(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    notification_id: uuid.UUID,
    run_context: dict[str, object] | None = None,
) -> NotificationStrategySimulationResult:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    notification = await _get_notification_or_404(
        db,
        user=user,
        project_id=project.id,
        notification_id=notification_id,
    )
    rule = dict(notification.rule_json or {})
    rollout_scope = dict(rule.get("rolloutScope") or {})
    return _build_strategy_simulation_result(
        notification_id=notification.id,
        rollout_scope=rollout_scope,
        run_context=run_context,
    )


def _build_strategy_simulation_result(
    *,
    notification_id: uuid.UUID,
    rollout_scope: dict[str, object],
    run_context: dict[str, object] | None = None,
) -> NotificationStrategySimulationResult:
    if not rollout_scope:
        return NotificationStrategySimulationResult(
            matched=True,
            scopeReason="ok",
            scopeDecision={},
            resolvedBatchPercent=None,
            resolvedPriority=100,
            resolvedLayer={},
            resolvedTimeWindow={},
            explanations=["no rolloutScope configured"],
            conflictCandidates=[],
        )

    result = simulate_rollout_scope(
        notification_id=notification_id,
        rollout_scope=rollout_scope,
        run_context=dict(run_context or {}),
    )
    return NotificationStrategySimulationResult(
        matched=result.matched,
        scopeReason=result.scope_reason,
        scopeDecision=result.scope_decision,
        resolvedBatchPercent=result.resolved_batch_percent,
        resolvedPriority=result.resolved_priority,
        resolvedLayer=result.resolved_layer,
        resolvedTimeWindow=result.resolved_time_window,
        explanations=list(result.explanations or []),
        conflictCandidates=list(result.conflict_candidates or []),
    )


async def simulate_notification_strategy_batch(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    notification_id: uuid.UUID,
    run_contexts: list[NotificationStrategySimulateRunContext],
) -> NotificationStrategySimulationBatchResult:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    notification = await _get_notification_or_404(
        db,
        user=user,
        project_id=project.id,
        notification_id=notification_id,
    )
    rule = dict(notification.rule_json or {})
    rollout_scope = dict(rule.get("rolloutScope") or {})

    items: list[NotificationStrategySimulationBatchItem] = []
    for run_context in run_contexts:
        result = _build_strategy_simulation_result(
            notification_id=notification.id,
            rollout_scope=rollout_scope,
            run_context=run_context.model_dump(),
        )
        items.append(
            NotificationStrategySimulationBatchItem(
                runContext=run_context,
                result=result,
            )
        )

    return NotificationStrategySimulationBatchResult(items=items)


def _to_delivery_list_item(row: NotificationOutbox) -> NotificationDeliveryListItem:
    return NotificationDeliveryListItem(
        id=str(row.id),
        projectId=str(row.project_id),
        runId=str(row.run_id),
        notificationId=str(row.notification_id),
        channel=row.channel,
        target=row.target,
        provider=row.provider,
        status=row.status,
        attempts=int(row.attempts or 0),
        maxRetries=int(row.max_retries or 0),
        nextRetryAt=to_unix_ts(row.next_retry_at),
        lastError=row.last_error,
        lastStatusCode=row.last_status_code,
        lastDurationMs=row.last_duration_ms,
        createdAt=to_unix_ts(row.created_at),
        updatedAt=to_unix_ts(row.updated_at),
    )


async def list_notification_deliveries(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    status: str | None,
    run_id: uuid.UUID | None,
    page: int,
    page_size: int,
) -> NotificationDeliveryListData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    where_clause = [
        NotificationOutbox.tenant_id == user.tenant_id,
        NotificationOutbox.project_id == project.id,
    ]
    if status:
        where_clause.append(NotificationOutbox.status == status.strip().upper())
    if run_id is not None:
        where_clause.append(NotificationOutbox.run_id == run_id)

    total = int(
        (
            await db.execute(
                select(func.count(NotificationOutbox.id)).where(*where_clause)
            )
        ).scalar_one()
        or 0
    )
    rows = (
        await db.execute(
            select(NotificationOutbox)
            .where(*where_clause)
            .order_by(desc(NotificationOutbox.created_at), desc(NotificationOutbox.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return NotificationDeliveryListData(
        page=page,
        pageSize=page_size,
        total=total,
        items=[_to_delivery_list_item(row) for row in rows],
    )


async def retry_notification_delivery(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    delivery_id: uuid.UUID,
) -> NotificationDeliveryRetryResult:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    row = await db.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.id == delivery_id,
            NotificationOutbox.project_id == project.id,
            NotificationOutbox.tenant_id == user.tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Delivery not found")

    status = str(row.status or "").upper()
    if status not in {"FAILED", "QUEUED"}:
        raise HTTPException(status_code=400, detail="Only FAILED/QUEUED delivery can be retried")

    row.status = "QUEUED"
    row.next_retry_at = None
    await db.flush()
    await process_notification_outbox_item(db, outbox=row)

    return NotificationDeliveryRetryResult(
        id=str(row.id),
        status=row.status,
        attempts=int(row.attempts or 0),
    )
