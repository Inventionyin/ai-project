from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable

import requests

WebhookProvider = Callable[..., object]
NotificationProvider = Callable[..., object]
IssueProvider = Callable[..., "IssueProviderResult"]

_WEBHOOK_DEFAULT_PROVIDER = "WEBHOOK"
_ISSUE_FALLBACK_PROVIDER = "GENERIC"

_webhook_providers: dict[str, WebhookProvider] = {}
_notification_providers: dict[tuple[str, str], NotificationProvider] = {}
_issue_providers: dict[str, IssueProvider] = {}


@dataclass(frozen=True, slots=True)
class IssueProviderResult:
    issue_key: str
    url: str


def _normalize_provider_name(value: str, *, field: str = "provider") -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        raise ValueError(f"invalid_{field}")
    return normalized[:64]


def register_webhook_provider(name: str, provider: WebhookProvider) -> None:
    key = _normalize_provider_name(name, field="webhook_provider")
    _webhook_providers[key] = provider
    register_notification_provider("WEBHOOK", key, provider)


def get_webhook_provider(name: str | None = None) -> WebhookProvider | None:
    key = _normalize_provider_name(name or _WEBHOOK_DEFAULT_PROVIDER, field="webhook_provider")
    provider = _webhook_providers.get(key)
    if provider is not None:
        return provider
    return get_notification_provider("WEBHOOK", key)


def list_webhook_providers() -> tuple[str, ...]:
    return tuple(sorted(_webhook_providers.keys()))


def _normalize_channel(value: str, *, field: str = "channel") -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        raise ValueError(f"invalid_{field}")
    return normalized[:32]


def register_notification_provider(channel: str, name: str, provider: NotificationProvider) -> None:
    channel_key = _normalize_channel(channel, field="notification_channel")
    provider_key = _normalize_provider_name(name, field="notification_provider")
    _notification_providers[(channel_key, provider_key)] = provider
    if channel_key == "WEBHOOK":
        _webhook_providers[provider_key] = provider


def get_notification_provider(channel: str, name: str | None = None) -> NotificationProvider | None:
    channel_key = _normalize_channel(channel, field="notification_channel")
    provider_name = name or ("WEBHOOK" if channel_key == "WEBHOOK" else channel_key)
    provider_key = _normalize_provider_name(provider_name, field="notification_provider")
    return _notification_providers.get((channel_key, provider_key))


def list_notification_providers(channel: str | None = None) -> tuple[str, ...] | dict[str, tuple[str, ...]]:
    if channel is None:
        indexed: dict[str, set[str]] = {}
        for channel_key, provider_key in _notification_providers.keys():
            indexed.setdefault(channel_key, set()).add(provider_key)
        return {key: tuple(sorted(values)) for key, values in sorted(indexed.items())}
    channel_key = _normalize_channel(channel, field="notification_channel")
    providers = sorted(
        provider_key
        for provider_channel, provider_key in _notification_providers.keys()
        if provider_channel == channel_key
    )
    return tuple(providers)


def register_issue_provider(name: str, provider: IssueProvider) -> None:
    key = _normalize_provider_name(name, field="issue_provider")
    _issue_providers[key] = provider


def resolve_issue_provider(name: str) -> IssueProvider | None:
    key = _normalize_provider_name(name, field="issue_provider")
    return _issue_providers.get(key) or _issue_providers.get(_ISSUE_FALLBACK_PROVIDER)


def list_issue_providers() -> tuple[str, ...]:
    return tuple(sorted(_issue_providers.keys()))


def _default_issue_provider(provider: str, *, url: str | None = None, **_: object) -> IssueProviderResult:
    issue_key = f"{provider}-{uuid.uuid4().hex[:8].upper()}"
    issue_url = str(url or "").strip() or f"https://{provider.lower()}.local/issues/{issue_key}"
    return IssueProviderResult(issue_key=issue_key, url=issue_url)


def _as_map(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _pick_str(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _jira_issue_provider(
    provider: str,
    *,
    title: str | None = None,
    description: str | None = None,
    project_key: str | None = None,
    issue_type: str | None = None,
    config: dict[str, object] | None = None,
    credentials: dict[str, object] | None = None,
    execute_request: bool | None = None,
    timeout: float | None = None,
    **_: object,
) -> IssueProviderResult:
    cfg = _as_map(config)
    creds = _as_map(credentials)
    base_url = _pick_str(cfg.get("baseUrl"), cfg.get("url"), cfg.get("host"))
    project = _pick_str(project_key, cfg.get("projectKey"), cfg.get("project"))
    issue_kind = _pick_str(issue_type, cfg.get("issueType"), "Task")
    email = _pick_str(creds.get("email"), cfg.get("email"))
    token = _pick_str(creds.get("token"), creds.get("apiToken"), cfg.get("token"))
    if not base_url:
        raise ValueError("jira_missing_base_url")
    if not project:
        raise ValueError("jira_missing_project_key")
    if not token:
        raise ValueError("jira_missing_token")
    if not email:
        raise ValueError("jira_missing_email")
    url = f"{base_url.rstrip('/')}/rest/api/3/issue"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {
        "fields": {
            "project": {"key": project},
            "summary": title or "Untitled issue",
            "description": description or "",
            "issuetype": {"name": issue_kind},
        }
    }
    if execute_request:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            auth=(email, token),
            timeout=timeout or 10,
        )
        response.raise_for_status()
        data = response.json()
        issue_key = str(data.get("key") or "").strip() or f"{provider}-{uuid.uuid4().hex[:8].upper()}"
        return IssueProviderResult(issue_key=issue_key, url=f"{base_url.rstrip('/')}/browse/{issue_key}")
    issue_key = f"{provider}-{uuid.uuid4().hex[:8].upper()}"
    return IssueProviderResult(issue_key=issue_key, url=f"{base_url.rstrip('/')}/browse/{issue_key}")


def _zentao_issue_provider(
    provider: str,
    *,
    title: str | None = None,
    description: str | None = None,
    config: dict[str, object] | None = None,
    credentials: dict[str, object] | None = None,
    execute_request: bool | None = None,
    timeout: float | None = None,
    **_: object,
) -> IssueProviderResult:
    cfg = _as_map(config)
    creds = _as_map(credentials)
    base_url = _pick_str(cfg.get("baseUrl"), cfg.get("url"), cfg.get("host"))
    product = cfg.get("product")
    module = cfg.get("module")
    execution = cfg.get("execution")
    token = _pick_str(creds.get("token"), cfg.get("token"))
    if not base_url:
        raise ValueError("zentao_missing_base_url")
    if product is None:
        raise ValueError("zentao_missing_product")
    if token is None or not str(token).strip():
        raise ValueError("zentao_missing_token")
    url = f"{base_url.rstrip('/')}/api.php/v1/bugs"
    headers = {"Content-Type": "application/json", "Token": str(token).strip()}
    payload: dict[str, object] = {
        "title": title or "Untitled issue",
        "steps": description or "",
        "product": product,
    }
    if module is not None:
        payload["module"] = module
    if execution is not None:
        payload["execution"] = execution
    if execute_request:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout or 10)
        response.raise_for_status()
        data = response.json()
        bug_data = data.get("bug") if isinstance(data, dict) else None
        bug_id = None
        if isinstance(bug_data, dict):
            bug_id = bug_data.get("id")
        if bug_id is None and isinstance(data, dict):
            bug_id = data.get("id")
        issue_key = f"{provider}-{str(bug_id).strip()}" if bug_id is not None else f"{provider}-{uuid.uuid4().hex[:8].upper()}"
        return IssueProviderResult(issue_key=issue_key, url=f"{base_url.rstrip('/')}/bug-view-{str(bug_id).strip()}.html" if bug_id is not None else f"{base_url.rstrip('/')}/bug-browse.html")
    issue_key = f"{provider}-{uuid.uuid4().hex[:8].upper()}"
    return IssueProviderResult(issue_key=issue_key, url=f"{base_url.rstrip('/')}/bug-browse.html")


register_issue_provider(_ISSUE_FALLBACK_PROVIDER, _default_issue_provider)
register_issue_provider("JIRA", _jira_issue_provider)
register_issue_provider("ZENTAO", _zentao_issue_provider)
for _alias in ("TAPD", "TEAMBITION"):
    register_issue_provider(_alias, _default_issue_provider)
