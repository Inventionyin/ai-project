from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import time
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass
from datetime import timezone
from typing import Any

import requests
from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CaseRunStatus, RunStatus
from app.models.integration import Notification, NotificationOutbox
from app.models.prompt_template import PromptTemplate
from app.models.project import Project
from app.models.run import CaseRun, Run
from app.services.provider_registry import get_notification_provider, register_notification_provider

_SUPPORTED_TEMPLATE_VARS = {
    "runId",
    "status",
    "projectName",
    "passRate",
    "failCount",
    "reportUrl",
}
_TEMPLATE_VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
_DEFAULT_TEMPLATE_SCENE_BY_CHANNEL = {
    "WEBHOOK": "NOTIFICATION_WEBHOOK",
    "EMAIL": "NOTIFICATION_EMAIL",
    "IM": "NOTIFICATION_IM",
}
_DINGTALK_TOKEN_PATTERN = re.compile(r"(access_token=)([^&\s]+)", re.IGNORECASE)


@dataclass(slots=True)
class DeliveryResult:
    ok: bool
    attempt_count: int
    status_code: int | None
    duration_ms: int
    error: str | None


@dataclass(slots=True)
class RolloutScopeMatchResult:
    matched: bool
    scope_reason: str
    scope_decision: dict[str, Any]
    resolved_batch_percent: int | None
    resolved_priority: int | None
    resolved_layer: dict[str, Any]
    resolved_time_window: dict[str, Any]
    explanations: list[str]
    conflict_candidates: list[dict[str, Any]]


def render_notification_template(template: str, variables: dict[str, Any]) -> str:
    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in _SUPPORTED_TEMPLATE_VARS:
            return match.group(0)
        value = variables.get(key, "")
        return "" if value is None else str(value)

    return _TEMPLATE_VAR_PATTERN.sub(_replace, template)


def build_webhook_headers(*, body: str, rule_json: dict[str, Any] | None = None) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    config = rule_json or {}
    secret = config.get("secret")
    if secret:
        signature = hmac.new(str(secret).encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
        headers["X-Signature"] = signature
    return headers


def deliver_webhook(
    *,
    target: str,
    payload: dict[str, Any],
    rule_json: dict[str, Any] | None = None,
    timeout: float = 5.0,
    max_retries: int = 3,
) -> DeliveryResult:
    attempts = max(1, int(max_retries))
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    headers = build_webhook_headers(body=body, rule_json=rule_json)

    started = time.perf_counter()
    final_status_code: int | None = None
    final_error: str | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(target, data=body.encode("utf-8"), headers=headers, timeout=timeout)
            final_status_code = response.status_code
            if 200 <= response.status_code < 300:
                duration_ms = int((time.perf_counter() - started) * 1000)
                return DeliveryResult(
                    ok=True,
                    attempt_count=attempt,
                    status_code=final_status_code,
                    duration_ms=duration_ms,
                    error=None,
                )
            final_error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            final_error = str(exc)

    duration_ms = int((time.perf_counter() - started) * 1000)
    return DeliveryResult(
        ok=False,
        attempt_count=attempts,
        status_code=final_status_code,
        duration_ms=duration_ms,
        error=final_error,
    )


def _build_dingtalk_text(payload: dict[str, Any], rule_json: dict[str, Any] | None = None) -> str:
    rule = dict(rule_json or {})
    keyword = str(rule.get("keyword") or "测试平台").strip() or "测试平台"
    custom_template = str(rule.get("template") or "").strip()
    if custom_template:
        content = render_notification_template(custom_template, payload)
        if keyword not in content:
            content = f"{keyword}：{content}"
        return content
    project_name = str(payload.get("projectName") or "-")
    run_id = str(payload.get("runId") or "-")
    status = str(payload.get("status") or "-")
    pass_rate = str(payload.get("passRate") or "-")
    fail_count = str(payload.get("failCount") or "0")
    report_url = str(payload.get("reportUrl") or "-")
    return (
        f"{keyword}：运行通知\n"
        f"项目：{project_name}\n"
        f"运行：{run_id}\n"
        f"状态：{status}\n"
        f"通过率：{pass_rate}\n"
        f"失败数：{fail_count}\n"
        f"报告：{report_url}"
    )


def deliver_dingtalk(
    *,
    target: str,
    payload: dict[str, Any],
    rule_json: dict[str, Any] | None = None,
    timeout: float = 5.0,
    max_retries: int = 3,
) -> DeliveryResult:
    attempts = max(1, int(max_retries))
    body = json.dumps(
        {
            "msgtype": "text",
            "text": {"content": _build_dingtalk_text(payload, rule_json)},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    headers: dict[str, str] = {"Content-Type": "application/json"}

    started = time.perf_counter()
    final_status_code: int | None = None
    final_error: str | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(target, data=body.encode("utf-8"), headers=headers, timeout=timeout)
            final_status_code = response.status_code
            if 200 <= response.status_code < 300:
                duration_ms = int((time.perf_counter() - started) * 1000)
                return DeliveryResult(ok=True, attempt_count=attempt, status_code=final_status_code, duration_ms=duration_ms, error=None)
            final_error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            final_error = _DINGTALK_TOKEN_PATTERN.sub(r"\1***", str(exc))

    duration_ms = int((time.perf_counter() - started) * 1000)
    return DeliveryResult(ok=False, attempt_count=attempts, status_code=final_status_code, duration_ms=duration_ms, error=final_error)


register_notification_provider("IM", "DINGTALK", deliver_dingtalk)


_TERMINAL_RUN_STATUSES = {RunStatus.PASSED, RunStatus.FAILED, RunStatus.CANCELED}
_STATUS_EVENT_MAP = {
    RunStatus.PASSED: "RUN_PASSED",
    RunStatus.FAILED: "RUN_FAILED",
    RunStatus.CANCELED: "RUN_CANCELED",
}
_RUN_FINISHED_EVENT = "RUN_FINISHED"


def _coerce_float(value: Any, *, default: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def _coerce_int(value: Any, *, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def _utcnow() -> datetime:
    return datetime.utcnow()


def _stable_bucket_for_canary(*, run_id: uuid.UUID, notification_id: uuid.UUID) -> int:
    digest = hashlib.sha256(f"{run_id}:{notification_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="big", signed=False) % 100


def _is_canary_selected(*, run_id: uuid.UUID, notification_id: uuid.UUID, percent: int) -> bool:
    bounded_percent = _coerce_int(percent, default=10, min_value=1, max_value=100)
    return _stable_bucket_for_canary(run_id=run_id, notification_id=notification_id) < bounded_percent


def _is_seed_selected(*, notification_id: uuid.UUID, seed: Any, percent: int) -> bool:
    bounded_percent = _coerce_int(percent, default=10, min_value=1, max_value=100)
    digest = hashlib.sha256(f"{seed}:{notification_id}".encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], byteorder="big", signed=False) % 100
    return bucket < bounded_percent


def _extract_run_meta_tags(run: Run) -> set[str]:
    summary = dict(run.summary_json or {})
    meta = summary.get("meta")
    if not isinstance(meta, dict):
        return set()
    tags = meta.get("tags")
    if not isinstance(tags, list):
        return set()
    return {str(tag).strip() for tag in tags if str(tag).strip()}


def _extract_run_meta_layer_value(run: Run, layer_key: str) -> str:
    summary = dict(run.summary_json or {})
    meta = summary.get("meta")
    if not isinstance(meta, dict):
        return ""
    layers = meta.get("layers")
    if isinstance(layers, dict):
        value = layers.get(layer_key)
        if value is not None:
            return str(value).strip()
    value = meta.get(layer_key)
    if value is not None:
        return str(value).strip()
    return ""


def _rollout_scope_time_window_matches(
    *,
    run: Run | None = None,
    run_context: dict[str, Any] | None = None,
    time_window: dict[str, Any],
) -> bool:
    weekdays = time_window.get("weekdays")
    start_hour = time_window.get("startHour")
    end_hour = time_window.get("endHour")
    timezone_offset_minutes = time_window.get("timezoneOffsetMinutes")

    if not isinstance(weekdays, list) and not isinstance(start_hour, int) and not isinstance(end_hour, int):
        return True

    run_weekday = run_context.get("weekday") if isinstance(run_context, dict) else None
    run_hour = run_context.get("hour") if isinstance(run_context, dict) else None
    run_tz_offset = run_context.get("timezoneOffsetMinutes") if isinstance(run_context, dict) else None
    if isinstance(run_weekday, int) and isinstance(run_hour, int):
        local_weekday = run_weekday
        local_hour = run_hour
    else:
        run_time = (
            getattr(run, "updated_at", None)
            or getattr(run, "end_at", None)
            or getattr(run, "start_at", None)
            or getattr(run, "created_at", None)
            or _utcnow()
        )
        if run_time.tzinfo is None:
            run_time_utc = run_time.replace(tzinfo=timezone.utc)
        else:
            run_time_utc = run_time.astimezone(timezone.utc)
        effective_offset = timezone_offset_minutes if isinstance(timezone_offset_minutes, int) else run_tz_offset
        if isinstance(effective_offset, int):
            run_time_local = run_time_utc + timedelta(minutes=effective_offset)
        else:
            run_time_local = run_time_utc
        local_weekday = run_time_local.isoweekday()
        local_hour = int(run_time_local.hour)

    if isinstance(weekdays, list) and weekdays:
        weekday_set = {int(day) for day in weekdays if isinstance(day, int)}
        if local_weekday not in weekday_set:
            return False

    if isinstance(start_hour, int) and isinstance(end_hour, int):
        hour = local_hour
        if start_hour == end_hour:
            return True
        if start_hour < end_hour:
            return start_hour <= hour < end_hour
        return hour >= start_hour or hour < end_hour
    return True


def _select_rollout_time_window(
    *,
    run: Run | None = None,
    run_context: dict[str, Any] | None = None,
    time_windows: list[Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    matched: list[tuple[int, int, int, dict[str, Any]]] = []
    for idx, item in enumerate(time_windows):
        if not isinstance(item, dict):
            continue
        enabled = item.get("enabled")
        if isinstance(enabled, bool) and not enabled:
            continue
        window_obj = item.get("timeWindow")
        if not isinstance(window_obj, dict):
            continue
        if not _rollout_scope_time_window_matches(run=run, run_context=run_context, time_window=window_obj):
            continue
        priority = _coerce_int(item.get("priority"), default=1000, min_value=1, max_value=1000)
        weight = _coerce_int(item.get("weight"), default=1, min_value=1, max_value=100)
        matched.append((priority, -weight, idx, item))

    if not matched:
        return None, {"matchedWindowCount": 0, "reason": "no_time_window_matched", "conflictCandidates": []}
    conflict_candidates = [
        {
            "id": (str(item.get("id")).strip() if isinstance(item.get("id"), str) else None),
            "priority": _coerce_int(item.get("priority"), default=1000, min_value=1, max_value=1000),
            "weight": _coerce_int(item.get("weight"), default=1, min_value=1, max_value=100),
        }
        for _, _, _, item in matched
    ]
    matched.sort(key=lambda x: (x[0], x[1], x[2]))
    selected = matched[0][3]
    selected_id_raw = selected.get("id")
    selected_id = str(selected_id_raw).strip() if isinstance(selected_id_raw, str) else ""
    return selected, {
        "selectedWindowId": selected_id or None,
        "matchedWindowCount": len(matched),
        "reason": "window_selected_by_priority_weight_order",
        "conflictCandidates": conflict_candidates,
    }


def _match_rollout_scope(
    *,
    run: Run,
    notification_id: uuid.UUID,
    rollout_scope: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None]:
    matched = evaluate_rollout_scope(run=run, notification_id=notification_id, rollout_scope=rollout_scope)
    return (None if matched.matched else matched.scope_reason), matched.scope_decision or None


def evaluate_rollout_scope(
    *,
    run: Run | None = None,
    notification_id: uuid.UUID,
    rollout_scope: dict[str, Any],
    run_context: dict[str, Any] | None = None,
) -> RolloutScopeMatchResult:
    context = dict(run_context or {})
    scope_decision: dict[str, Any] = {}
    explanations: list[str] = []
    conflict_candidates: list[dict[str, Any]] = []
    resolved_priority = _coerce_int(rollout_scope.get("priority"), default=100, min_value=1, max_value=1000)
    resolved_layer: dict[str, Any] = {}
    resolved_time_window: dict[str, Any] = {}

    env_ids = rollout_scope.get("envIds")
    if isinstance(env_ids, list) and env_ids:
        run_env_id_raw = context.get("envId")
        if run_env_id_raw is None and run is not None:
            run_env_id_raw = getattr(run, "env_id", None)
        run_env_id = str(run_env_id_raw).strip().lower() if run_env_id_raw is not None else ""
        scope_env_ids = {str(item).strip().lower() for item in env_ids if str(item).strip()}
        if run_env_id not in scope_env_ids:
            explanations.append("env filtered")
            return RolloutScopeMatchResult(False, "scope_env_filtered", scope_decision, None, resolved_priority, resolved_layer, resolved_time_window, explanations, conflict_candidates)
        explanations.append("env matched")

    trigger_types = rollout_scope.get("triggerTypes")
    if isinstance(trigger_types, list) and trigger_types:
        run_trigger_type_raw = context.get("triggerType")
        if run_trigger_type_raw is None and run is not None:
            run_trigger_type_raw = getattr(run, "trigger_type", None)
        run_trigger_type = str(run_trigger_type_raw.value if hasattr(run_trigger_type_raw, "value") else run_trigger_type_raw).strip().upper()
        scope_trigger_types = {str(item).strip().upper() for item in trigger_types if str(item).strip()}
        if run_trigger_type not in scope_trigger_types:
            explanations.append("trigger filtered")
            return RolloutScopeMatchResult(False, "scope_trigger_filtered", scope_decision, None, resolved_priority, resolved_layer, resolved_time_window, explanations, conflict_candidates)
        explanations.append("trigger matched")

    meta_tags = rollout_scope.get("metaTags")
    if isinstance(meta_tags, list) and meta_tags:
        run_meta_tags_raw = context.get("metaTags")
        if isinstance(run_meta_tags_raw, list):
            run_meta_tags = {str(tag).strip() for tag in run_meta_tags_raw if str(tag).strip()}
        elif run is not None:
            run_meta_tags = _extract_run_meta_tags(run)
        else:
            run_meta_tags = set()
        scope_meta_tags = {str(item).strip() for item in meta_tags if str(item).strip()}
        if not run_meta_tags or not (run_meta_tags & scope_meta_tags):
            explanations.append("metaTags filtered")
            return RolloutScopeMatchResult(False, "scope_meta_tag_filtered", scope_decision, None, resolved_priority, resolved_layer, resolved_time_window, explanations, conflict_candidates)
        explanations.append("metaTags matched")

    layer_key = rollout_scope.get("layerKey")
    layer_values = rollout_scope.get("layerValues")
    if isinstance(layer_key, str) and layer_key.strip() and isinstance(layer_values, list) and layer_values:
        run_layer_value_raw = context.get("layerValue")
        if run_layer_value_raw is None and run is not None:
            run_layer_value_raw = _extract_run_meta_layer_value(run, layer_key.strip())
        run_layer_value = str(run_layer_value_raw or "").strip()
        scope_layer_values = {str(item).strip() for item in layer_values if str(item).strip()}
        if run_layer_value not in scope_layer_values:
            explanations.append("layer filtered")
            return RolloutScopeMatchResult(False, "scope_layer_filtered", scope_decision, None, resolved_priority, resolved_layer, resolved_time_window, explanations, conflict_candidates)
        resolved_layer = {"layerKey": layer_key.strip(), "layerValue": run_layer_value}
        explanations.append("layer matched")

    effective_batch_percent = rollout_scope.get("batchPercent")
    time_windows = rollout_scope.get("timeWindows")
    if isinstance(time_windows, list):
        selected_window, scope_decision = _select_rollout_time_window(run=run, run_context=context, time_windows=time_windows)
        conflict_candidates = list(scope_decision.get("conflictCandidates") or [])
        if selected_window is None:
            explanations.append("timeWindow filtered")
            return RolloutScopeMatchResult(False, "scope_time_window_filtered", scope_decision, None, resolved_priority, resolved_layer, resolved_time_window, explanations, conflict_candidates)
        selected_batch_percent = selected_window.get("batchPercent")
        if isinstance(selected_batch_percent, int):
            effective_batch_percent = selected_batch_percent
        selected_window_id = str(selected_window.get("id") or "").strip()
        if selected_window_id:
            explanations.append(f"selected timeWindow {selected_window_id} by priority/weight")
        else:
            explanations.append("selected timeWindow by priority/weight")
        resolved_time_window = {
            "id": selected_window.get("id"),
            "priority": _coerce_int(selected_window.get("priority"), default=1000, min_value=1, max_value=1000),
            "weight": _coerce_int(selected_window.get("weight"), default=1, min_value=1, max_value=100),
            "batchPercent": selected_batch_percent if isinstance(selected_batch_percent, int) else None,
            "timeWindow": dict(selected_window.get("timeWindow") or {}),
        }

    time_window = rollout_scope.get("timeWindow")
    if isinstance(time_window, dict):
        if not _rollout_scope_time_window_matches(run=run, run_context=context, time_window=time_window):
            explanations.append("timeWindow filtered")
            return RolloutScopeMatchResult(False, "scope_time_window_filtered", scope_decision, None, resolved_priority, resolved_layer, resolved_time_window, explanations, conflict_candidates)
        explanations.append("timeWindow matched")

    batch_percent = effective_batch_percent
    if isinstance(batch_percent, int):
        if run is not None:
            matched_batch = _is_canary_selected(run_id=run.id, notification_id=notification_id, percent=batch_percent)
        else:
            seed = context.get("seed")
            if seed is None:
                seed = json.dumps(context, sort_keys=True, ensure_ascii=False)
            matched_batch = _is_seed_selected(notification_id=notification_id, seed=seed, percent=batch_percent)
        if not matched_batch:
            explanations.append("batchPercent filtered")
            return RolloutScopeMatchResult(False, "scope_batch_filtered", scope_decision, batch_percent, resolved_priority, resolved_layer, resolved_time_window, explanations, conflict_candidates)
        explanations.append("batchPercent matched")
    return RolloutScopeMatchResult(True, "ok", scope_decision, batch_percent if isinstance(batch_percent, int) else None, resolved_priority, resolved_layer, resolved_time_window, explanations, conflict_candidates)


def simulate_rollout_scope(
    *,
    notification_id: uuid.UUID,
    rollout_scope: dict[str, Any],
    run_context: dict[str, Any] | None = None,
) -> RolloutScopeMatchResult:
    return evaluate_rollout_scope(
        run=None,
        notification_id=notification_id,
        rollout_scope=rollout_scope,
        run_context=run_context,
    )


def _normalize_template_scene(channel: str, raw_scene: Any) -> str:
    channel_key = str(channel or "").strip().upper() or "WEBHOOK"
    default_scene = _DEFAULT_TEMPLATE_SCENE_BY_CHANNEL.get(channel_key, _DEFAULT_TEMPLATE_SCENE_BY_CHANNEL["WEBHOOK"])
    normalized = str(raw_scene or "").strip().upper()
    if not normalized:
        return default_scene
    # backward compatibility: allow legacy scene aliases WEBHOOK/EMAIL/IM
    return _DEFAULT_TEMPLATE_SCENE_BY_CHANNEL.get(normalized, normalized)


def _resolve_provider(outbox: NotificationOutbox) -> Any | None:
    channel = str(getattr(outbox, "channel", "") or "").strip().upper() or "WEBHOOK"
    provider_name = str(getattr(outbox, "provider", "") or "").strip().upper() or channel
    provider = get_notification_provider(channel, provider_name)
    if provider is None and channel == "WEBHOOK" and provider_name == "WEBHOOK":
        provider = deliver_webhook
    return provider


def _next_retry_at(*, now: datetime, attempts: int, base_seconds: int) -> datetime:
    delay_seconds = max(1, int(base_seconds)) * (2 ** max(0, attempts - 1))
    return now + timedelta(seconds=delay_seconds)


async def _resolve_notification_template(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    channel: str,
    rule_json: dict[str, Any],
    run_id: uuid.UUID | None = None,
    notification_id: uuid.UUID | None = None,
) -> tuple[str | None, dict[str, str] | None]:
    inline_template = str(rule_json.get("template") or "").strip()
    if inline_template:
        return inline_template, {"mode": "INLINE"}

    template_name = str(rule_json.get("templateName") or "").strip()
    if not template_name:
        return None, None

    template_scene = _normalize_template_scene(channel, rule_json.get("templateScene"))
    template_version = str(rule_json.get("templateVersion") or "").strip()
    base_stmt = select(PromptTemplate).where(
        PromptTemplate.tenant_id == tenant_id,
        PromptTemplate.project_id == project_id,
        PromptTemplate.scene == template_scene,
        PromptTemplate.name == template_name,
    )
    if template_version:
        version_stmt = (
            base_stmt.where(PromptTemplate.version == template_version)
            .order_by(desc(PromptTemplate.updated_at), desc(PromptTemplate.created_at), desc(PromptTemplate.id))
        )
        row = await db.scalar(version_stmt)
        if not isinstance(row, PromptTemplate):
            return None, None
        content = str(row.content or "").strip()
        if not content:
            return None, None
        selected_version = str(row.version)
        return content, {
            "mode": "VERSIONED",
            "scene": template_scene,
            "name": template_name,
            "version": selected_version,
            "selectedVersion": selected_version,
        }

    active_stmt = (
        base_stmt.where(PromptTemplate.is_active.is_(True))
        .order_by(desc(PromptTemplate.updated_at), desc(PromptTemplate.created_at), desc(PromptTemplate.id))
    )
    active_row = await db.scalar(active_stmt)
    if not isinstance(active_row, PromptTemplate):
        return None, None
    active_content = str(active_row.content or "").strip()
    if not active_content:
        return None, None

    active_version = str(active_row.version)
    selected_mode = "ACTIVE"
    selected_version = active_version
    selected_content = active_content

    strategy_raw = str(rule_json.get("templateStrategy") or "ACTIVE").strip().upper()
    strategy = "CANARY" if strategy_raw == "CANARY" else "ACTIVE"
    canary_version = str(rule_json.get("templateCanaryVersion") or "").strip()
    canary_percent = _coerce_int(rule_json.get("templateCanaryPercent"), default=10, min_value=1, max_value=100)

    if (
        strategy == "CANARY"
        and canary_version
        and run_id is not None
        and notification_id is not None
        and canary_version != active_version
        and _is_canary_selected(run_id=run_id, notification_id=notification_id, percent=canary_percent)
    ):
        canary_stmt = (
            base_stmt.where(PromptTemplate.version == canary_version)
            .order_by(desc(PromptTemplate.updated_at), desc(PromptTemplate.created_at), desc(PromptTemplate.id))
        )
        canary_row = await db.scalar(canary_stmt)
        if isinstance(canary_row, PromptTemplate):
            canary_content = str(canary_row.content or "").strip()
            if canary_content:
                selected_mode = "CANARY"
                selected_version = str(canary_row.version)
                selected_content = canary_content

    content = str(selected_content or "").strip()
    if not content:
        return None, None
    return content, {
        "mode": selected_mode,
        "scene": template_scene,
        "name": template_name,
        "version": selected_version,
        "selectedVersion": selected_version,
        "canaryVersion": canary_version,
        "activeVersion": active_version,
    }


async def process_notification_outbox_item(
    db: AsyncSession,
    *,
    outbox: NotificationOutbox,
    retry_base_seconds: int = 5,
) -> None:
    provider = _resolve_provider(outbox)
    if provider is None:
        outbox.attempts = int(outbox.attempts or 0) + 1
        outbox.status = "FAILED"
        outbox.last_error = "unsupported_provider"
        outbox.last_status_code = None
        outbox.last_duration_ms = 0
        outbox.next_retry_at = None
        await db.flush()
        return

    timeout = _coerce_float((outbox.rule_json or {}).get("timeoutSec"), default=5.0, min_value=0.1, max_value=30.0)
    try:
        result = await asyncio.to_thread(
            provider,
            target=outbox.target,
            payload=dict(outbox.payload_json or {}),
            rule_json=dict(outbox.rule_json or {}),
            timeout=timeout,
            max_retries=1,
        )
    except Exception as exc:  # defensive guard for custom provider runtime failures
        result = DeliveryResult(
            ok=False,
            attempt_count=1,
            status_code=None,
            duration_ms=0,
            error=str(exc)[:300],
        )
    attempts = int(outbox.attempts or 0) + 1
    max_retries = max(1, int(outbox.max_retries or 1))
    outbox.attempts = attempts
    outbox.last_status_code = result.status_code
    outbox.last_duration_ms = int(result.duration_ms or 0)
    outbox.last_error = (str(result.error)[:500] if result.error else None)

    now = _utcnow()
    if result.ok:
        outbox.status = "SENT"
        outbox.next_retry_at = None
    elif attempts >= max_retries:
        outbox.status = "FAILED"
        outbox.next_retry_at = None
    else:
        outbox.status = "QUEUED"
        outbox.next_retry_at = _next_retry_at(now=now, attempts=attempts, base_seconds=retry_base_seconds)
    await db.flush()


async def process_due_notification_deliveries(
    db: AsyncSession,
    *,
    batch_size: int = 20,
    retry_base_seconds: int = 5,
) -> int:
    now = _utcnow()
    rows = (
        await db.execute(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.status == "QUEUED",
                or_(
                    NotificationOutbox.next_retry_at.is_(None),
                    NotificationOutbox.next_retry_at <= now,
                ),
            )
            .order_by(NotificationOutbox.created_at.asc(), NotificationOutbox.id.asc())
            .limit(max(1, int(batch_size)))
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()
    for row in rows:
        await process_notification_outbox_item(db, outbox=row, retry_base_seconds=retry_base_seconds)
    return len(rows)


async def run_notification_outbox_consumer(
    *,
    stop_event: asyncio.Event,
    sessionmaker: Any,
    poll_interval_seconds: float,
    batch_size: int,
    retry_base_seconds: int,
) -> None:
    while not stop_event.is_set():
        try:
            async with sessionmaker() as db:
                processed = await process_due_notification_deliveries(
                    db,
                    batch_size=batch_size,
                    retry_base_seconds=retry_base_seconds,
                )
                if processed > 0:
                    await db.commit()
        except Exception:
            # keep loop alive; errors will be retried in subsequent polling rounds.
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(0.1, float(poll_interval_seconds)))
        except asyncio.TimeoutError:
            continue


async def dispatch_run_terminal_notification(db: AsyncSession, *, run: Run) -> bool:
    if run.status not in _TERMINAL_RUN_STATUSES:
        return False
    summary = dict(run.summary_json or {})
    dispatch_state = dict(summary.get("notificationDispatch") or {})
    terminal_state = dict(dispatch_state.get("terminal") or {})
    if summary.get("notificationDispatchedAt") or terminal_state.get("dispatchedAt"):
        return False

    project_name = ""
    project = await db.scalar(select(Project).where(Project.id == run.project_id, Project.tenant_id == run.tenant_id))
    if project is not None:
        project_name = str(project.name or "")

    failed_count = int(
        (
            await db.execute(
                select(func.count(CaseRun.id)).where(
                    CaseRun.tenant_id == run.tenant_id,
                    CaseRun.run_id == run.id,
                    CaseRun.status == CaseRunStatus.FAILED,
                )
            )
        ).scalar_one()
        or 0
    )
    passed_count = int(
        (
            await db.execute(
                select(func.count(CaseRun.id)).where(
                    CaseRun.tenant_id == run.tenant_id,
                    CaseRun.run_id == run.id,
                    CaseRun.status == CaseRunStatus.PASSED,
                )
            )
        ).scalar_one()
        or 0
    )
    total_count = int(
        (
            await db.execute(
                select(func.count(CaseRun.id)).where(
                    CaseRun.tenant_id == run.tenant_id,
                    CaseRun.run_id == run.id,
                )
            )
        ).scalar_one()
        or 0
    )
    pass_rate = f"{((passed_count * 100.0 / total_count) if total_count > 0 else 0.0):.2f}%"

    execution_result = dict(summary.get("executionResult") or {})
    report_url = str(execution_result.get("reportUrl") or execution_result.get("reportPath") or "").strip()
    if not report_url:
        report_url = f"/api/runs/{run.id}"
    payload = {
        "runId": str(run.id),
        "status": run.status.value,
        "projectName": project_name,
        "passRate": pass_rate,
        "failCount": failed_count,
        "reportUrl": report_url,
    }

    event_name = _STATUS_EVENT_MAP[run.status]
    notify_rule_id = str(summary.get("notifyRuleId") or "").strip()
    stmt = select(Notification).where(
        Notification.tenant_id == run.tenant_id,
        Notification.project_id == run.project_id,
        Notification.enabled.is_(True),
    )
    if notify_rule_id:
        try:
            stmt = stmt.where(Notification.id == uuid.UUID(notify_rule_id))
        except ValueError:
            pass
    rows = (await db.execute(stmt)).scalars().all()

    indexed_results: dict[int, dict[str, Any]] = {}
    outbox_by_index: dict[int, NotificationOutbox] = {}
    sent = 0
    failed = 0
    skipped = 0
    delivery_tasks: list[asyncio.Task[tuple[int, dict[str, Any]]]] = []
    auto_rollback_candidates: dict[int, dict[str, Any]] = {}
    scope_decision_by_index: dict[int, dict[str, Any]] = {}

    async def _deliver_one(
        idx: int,
        *,
        notification_id: str,
        target: str,
        provider: Any,
        provider_name: str,
        delivery_payload: dict[str, Any],
        rule_json: dict[str, Any],
        timeout: float,
        max_retries: int,
        template_ref: dict[str, str] | None = None,
        template_reason: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        try:
            result = await asyncio.to_thread(
                provider,
                target=target,
                payload=delivery_payload,
                rule_json=rule_json,
                timeout=timeout,
                max_retries=max_retries,
            )
        except Exception as exc:  # defensive guard
            return idx, {
                "notificationId": notification_id,
                "ok": False,
                "attemptCount": 0,
                "statusCode": None,
                "durationMs": 0,
                "error": str(exc)[:300],
                "provider": provider_name,
                **({"templateRef": template_ref} if template_ref else {}),
                **({"templateReason": template_reason} if template_reason else {}),
            }
        response = {
            "notificationId": notification_id,
            "ok": bool(result.ok),
            "attemptCount": int(result.attempt_count),
            "statusCode": result.status_code,
            "durationMs": int(result.duration_ms),
            "error": result.error,
            "provider": provider_name,
        }
        if template_ref:
            response["templateRef"] = template_ref
        if template_reason:
            response["templateReason"] = template_reason
        return idx, response

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            _coerce_int(
                dict(getattr(row, "rule_json", {}) or {}).get("rolloutScope", {}).get("priority"),
                default=100,
                min_value=1,
                max_value=1000,
            ),
            str(getattr(row, "created_at", "") or ""),
            str(getattr(row, "id", "") or ""),
        ),
    )

    for idx, row in enumerate(sorted_rows):
        channel = str(row.channel or "").strip().upper() or "WEBHOOK"
        rule_json = dict(row.rule_json or {})
        events = rule_json.get("events")
        if isinstance(events, list):
            event_set = {str(x).strip().upper() for x in events if str(x).strip()}
            if event_set and event_name not in event_set and _RUN_FINISHED_EVENT not in event_set:
                skipped += 1
                indexed_results[idx] = {"notificationId": str(row.id), "ok": False, "reason": "event_filtered"}
                continue
        rollout_scope = rule_json.get("rolloutScope")
        if isinstance(rollout_scope, dict):
            scope_reason, scope_decision = _match_rollout_scope(
                run=run,
                notification_id=row.id,
                rollout_scope=rollout_scope,
            )
            if scope_decision is not None:
                scope_decision_by_index[idx] = scope_decision
            if scope_reason:
                skipped += 1
                response: dict[str, Any] = {
                    "notificationId": str(row.id),
                    "ok": False,
                    "reason": "scope_filtered",
                    "scopeReason": scope_reason,
                }
                if scope_decision is not None:
                    response["scopeDecision"] = scope_decision
                indexed_results[idx] = response
                continue

        delivery_payload = dict(payload)
        template_ref: dict[str, str] | None = None
        template_reason: str | None = None
        template_name = str(rule_json.get("templateName") or "").strip()
        template_version = str(rule_json.get("templateVersion") or "").strip()
        has_template_reference = bool(template_name or template_version)
        template, template_ref = await _resolve_notification_template(
            db,
            tenant_id=run.tenant_id,
            project_id=run.project_id,
            channel=channel,
            rule_json=rule_json,
            run_id=run.id,
            notification_id=row.id,
        )
        if template:
            delivery_payload["summary"] = render_notification_template(template, payload)
        elif has_template_reference:
            template_reason = "template_not_found"
        if template_ref:
            delivery_payload["templateRef"] = template_ref

        auto_rollback_candidates[idx] = {
            "enabled": bool(rule_json.get("autoRollbackEnabled")),
            "threshold": _coerce_int(rule_json.get("autoRollbackFailureThreshold"), default=3, min_value=1, max_value=20),
            "templateRef": dict(template_ref or {}),
            "notificationId": str(row.id),
            "ruleTemplateStrategy": str(rule_json.get("templateStrategy") or "ACTIVE").strip().upper(),
        }
        timeout = _coerce_float(rule_json.get("timeoutSec"), default=5.0, min_value=0.1, max_value=30.0)
        max_retries = _coerce_int(rule_json.get("maxRetries"), default=3, min_value=1, max_value=5)
        provider_name = str(rule_json.get("provider") or channel).strip().upper() or channel
        provider = get_notification_provider(channel, provider_name)
        if provider is None and channel == "WEBHOOK" and provider_name == "WEBHOOK":
            provider = deliver_webhook
        if provider is None:
            skipped += 1
            indexed_results[idx] = {
                "notificationId": str(row.id),
                "ok": False,
                "reason": "unsupported_provider",
                "provider": provider_name,
            }
            continue

        outbox = NotificationOutbox(
            tenant_id=run.tenant_id,
            project_id=run.project_id,
            run_id=run.id,
            notification_id=row.id,
            channel=channel,
            target=row.target,
            provider=provider_name,
            payload_json=delivery_payload,
            rule_json=rule_json,
            status="QUEUED",
            attempts=0,
            max_retries=max_retries,
            next_retry_at=None,
        )
        db.add(outbox)
        outbox_by_index[idx] = outbox

        delivery_tasks.append(
            asyncio.create_task(
                _deliver_one(
                    idx,
                    notification_id=str(row.id),
                    target=row.target,
                    provider=provider,
                    provider_name=provider_name,
                    delivery_payload=delivery_payload,
                    rule_json=rule_json,
                    timeout=timeout,
                    max_retries=max_retries,
                    template_ref=template_ref,
                    template_reason=template_reason,
                )
            )
        )

    if outbox_by_index:
        await db.flush()

    if delivery_tasks:
        delivered = await asyncio.gather(*delivery_tasks)
        for idx, result in delivered:
            scope_decision = scope_decision_by_index.get(idx)
            if scope_decision is not None:
                result["scopeDecision"] = scope_decision
            indexed_results[idx] = result
            outbox = outbox_by_index.get(idx)
            if outbox is None:
                continue
            outbox.attempts = int(result.get("attemptCount") or 0)
            outbox.last_status_code = result.get("statusCode")
            outbox.last_duration_ms = int(result.get("durationMs") or 0)
            outbox.last_error = (str(result.get("error"))[:500] if result.get("error") else None)
            outbox.status = "SENT" if result.get("ok") else "FAILED"
            outbox.next_retry_at = None
    dispatch_results: list[dict[str, Any]] = []
    for idx in range(len(rows)):
        result = indexed_results.get(idx)
        if result is None:
            continue
        if "reason" in result:
            dispatch_results.append(result)
            continue
        if result.get("ok"):
            sent += 1
        else:
            failed += 1
        dispatch_results.append(result)

    rollback_groups: dict[tuple[str, str, str, str, int], dict[str, Any]] = {}
    for idx, result in indexed_results.items():
        candidate = auto_rollback_candidates.get(idx)
        if not candidate or not candidate.get("enabled"):
            continue
        template_ref = dict(candidate.get("templateRef") or {})
        if str(template_ref.get("mode") or "").upper() != "CANARY":
            continue
        if bool(result.get("ok")):
            continue
        scene = str(template_ref.get("scene") or "").strip()
        name = str(template_ref.get("name") or "").strip()
        active_version = str(template_ref.get("activeVersion") or "").strip()
        canary_version = str(template_ref.get("canaryVersion") or "").strip()
        threshold = int(candidate.get("threshold") or 3)
        if not scene or not name or not active_version or not canary_version:
            continue
        key = (scene, name, active_version, canary_version, threshold)
        group = rollback_groups.get(key)
        if group is None:
            group = {
                "scene": scene,
                "name": name,
                "activeVersion": active_version,
                "canaryVersion": canary_version,
                "failureCount": 0,
                "threshold": threshold,
            }
            rollback_groups[key] = group
        group["failureCount"] = int(group["failureCount"]) + 1

    auto_rollback_actions: list[dict[str, Any]] = []
    for group in rollback_groups.values():
        failure_count = int(group["failureCount"])
        threshold = int(group["threshold"])
        should_rollback = failure_count >= threshold
        action = dict(group)
        action["triggered"] = should_rollback
        action["reason"] = "threshold_reached" if should_rollback else "threshold_not_reached"
        if should_rollback and group["activeVersion"] != group["canaryVersion"]:
            await db.execute(
                update(PromptTemplate)
                .where(
                    PromptTemplate.tenant_id == run.tenant_id,
                    PromptTemplate.project_id == run.project_id,
                    PromptTemplate.scene == group["scene"],
                    PromptTemplate.name == group["name"],
                    PromptTemplate.version == group["canaryVersion"],
                )
                .values(is_active=False)
            )
            await db.execute(
                update(PromptTemplate)
                .where(
                    PromptTemplate.tenant_id == run.tenant_id,
                    PromptTemplate.project_id == run.project_id,
                    PromptTemplate.scene == group["scene"],
                    PromptTemplate.name == group["name"],
                    PromptTemplate.version == group["activeVersion"],
                )
                .values(is_active=True)
            )
        auto_rollback_actions.append(action)

    if auto_rollback_actions:
        any_triggered = any(bool(item.get("triggered")) for item in auto_rollback_actions)
        auto_rollback_state: dict[str, Any] = {
            "triggered": any_triggered,
            "reason": "threshold_reached" if any_triggered else "threshold_not_reached",
            "actions": auto_rollback_actions,
        }
    else:
        auto_rollback_state = {
            "triggered": False,
            "reason": "not_applicable",
            "actions": [],
        }

    summary["notificationDispatch"] = {
        "terminal": {
            "event": event_name,
            "payload": payload,
            "results": dispatch_results,
            "ruleCount": len(rows),
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "autoRollback": auto_rollback_state,
            "dispatchedAt": int(datetime.utcnow().timestamp()),
        }
    }
    summary["notificationDispatchedAt"] = datetime.utcnow().isoformat()
    run.summary_json = summary
    return True
