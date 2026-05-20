from __future__ import annotations

import pytest

from app.services.provider_registry import (
    IssueProviderResult,
    _jira_issue_provider,
    _zentao_issue_provider,
    get_notification_provider,
    get_webhook_provider,
    register_notification_provider,
    register_issue_provider,
    register_webhook_provider,
    resolve_issue_provider,
)


def test_resolve_issue_provider_falls_back_to_generic() -> None:
    provider = resolve_issue_provider("ACME")
    assert provider is not None
    result = provider("ACME", url=None)
    assert result.issue_key.startswith("ACME-")
    assert result.url.startswith("https://acme.local/issues/")


def test_register_issue_provider_overrides_named_provider() -> None:
    def _custom_issue_provider(provider: str, **kwargs) -> IssueProviderResult:
        return IssueProviderResult(issue_key=f"{provider}-CUSTOM", url="https://custom.local/issues/1")

    register_issue_provider("ACME", _custom_issue_provider)
    provider = resolve_issue_provider("ACME")
    assert provider is _custom_issue_provider
    result = provider("ACME")
    assert result.issue_key == "ACME-CUSTOM"
    assert result.url == "https://custom.local/issues/1"


def test_register_webhook_provider_then_get() -> None:
    def _custom_webhook_provider(**kwargs):
        return {"ok": True}

    register_webhook_provider("CUSTOM_WEBHOOK", _custom_webhook_provider)
    provider = get_webhook_provider("CUSTOM_WEBHOOK")
    assert provider is _custom_webhook_provider


def test_register_notification_provider_then_get_by_channel() -> None:
    def _custom_email_provider(**kwargs):
        return {"ok": True}

    register_notification_provider("EMAIL", "CUSTOM_EMAIL", _custom_email_provider)
    provider = get_notification_provider("EMAIL", "CUSTOM_EMAIL")
    assert provider is _custom_email_provider
    assert get_notification_provider("IM", "CUSTOM_EMAIL") is None


def test_get_notification_provider_uses_channel_default_provider_name() -> None:
    def _custom_im_provider(**kwargs):
        return {"ok": True}

    register_notification_provider("IM", "IM", _custom_im_provider)
    provider = get_notification_provider("IM")
    assert provider is _custom_im_provider


def test_jira_provider_builds_request_with_stubbed_post(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"key": "JIRA-123"}

    def _fake_post(url, *, json, headers, auth, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["auth"] = auth
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr("app.services.provider_registry.requests.post", _fake_post)
    result = _jira_issue_provider(
        "JIRA",
        title="bug title",
        description="bug desc",
        project_key="QA",
        issue_type="Bug",
        config={"baseUrl": "https://jira.example.com"},
        credentials={"email": "u@example.com", "token": "tkn"},
        execute_request=True,
    )
    assert result.issue_key == "JIRA-123"
    assert result.url == "https://jira.example.com/browse/JIRA-123"
    assert captured["url"] == "https://jira.example.com/rest/api/3/issue"
    assert captured["auth"] == ("u@example.com", "tkn")
    assert captured["headers"] == {"Accept": "application/json", "Content-Type": "application/json"}
    assert captured["json"] == {
        "fields": {
            "project": {"key": "QA"},
            "summary": "bug title",
            "description": "bug desc",
            "issuetype": {"name": "Bug"},
        }
    }


def test_zentao_provider_builds_request_with_stubbed_post(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"bug": {"id": 9}}

    def _fake_post(url, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr("app.services.provider_registry.requests.post", _fake_post)
    result = _zentao_issue_provider(
        "ZENTAO",
        title="zentao title",
        description="zentao steps",
        config={"baseUrl": "https://zentao.example.com", "product": 3, "module": 11, "execution": 22},
        credentials={"token": "zt"},
        execute_request=True,
    )
    assert result.issue_key == "ZENTAO-9"
    assert result.url == "https://zentao.example.com/bug-view-9.html"
    assert captured["url"] == "https://zentao.example.com/api.php/v1/bugs"
    assert captured["headers"] == {"Content-Type": "application/json", "Token": "zt"}
    assert captured["json"] == {
        "title": "zentao title",
        "steps": "zentao steps",
        "product": 3,
        "module": 11,
        "execution": 22,
    }
