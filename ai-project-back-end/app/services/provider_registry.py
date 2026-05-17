from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable

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


register_issue_provider(_ISSUE_FALLBACK_PROVIDER, _default_issue_provider)
for _alias in ("JIRA", "ZENTAO", "TAPD", "TEAMBITION"):
    register_issue_provider(_alias, _default_issue_provider)
