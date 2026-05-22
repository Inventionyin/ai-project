from __future__ import annotations

import json

import requests

from app.services.integration_delivery import _normalize_template_scene, deliver_dingtalk, deliver_webhook, render_notification_template
from app.services.provider_registry import get_notification_provider


def test_render_notification_template_replaces_supported_variables() -> None:
    template = (
        "run={{runId}},status={{status}},project={{projectName}},"
        "pass={{passRate}},fail={{failCount}},report={{reportUrl}}"
    )
    rendered = render_notification_template(
        template,
        {
            "runId": "r-001",
            "status": "FAILED",
            "projectName": "Demo",
            "passRate": "92.5%",
            "failCount": 3,
            "reportUrl": "https://example.com/report/r-001",
        },
    )
    assert rendered == (
        "run=r-001,status=FAILED,project=Demo,pass=92.5%,fail=3,"
        "report=https://example.com/report/r-001"
    )


def test_deliver_webhook_retries_until_third_success(monkeypatch) -> None:
    class _Resp:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    call_count = {"n": 0}

    def _fake_post(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] <= 2:
            raise requests.Timeout("timeout")
        return _Resp(200)

    monkeypatch.setattr("app.services.integration_delivery.requests.post", _fake_post)
    result = deliver_webhook(
        target="https://hooks.example.com",
        payload={"runId": "r-002"},
        max_retries=3,
    )
    assert result.ok is True
    assert result.attempt_count == 3
    assert result.status_code == 200


def test_deliver_webhook_adds_signature_header_when_secret_exists(monkeypatch) -> None:
    captured_headers = {}

    class _Resp:
        status_code = 200

    def _fake_post(*args, **kwargs):
        captured_headers.update(kwargs["headers"])
        return _Resp()

    monkeypatch.setattr("app.services.integration_delivery.requests.post", _fake_post)
    result = deliver_webhook(
        target="https://hooks.example.com",
        payload={"status": "PASSED"},
        rule_json={"secret": "top-secret"},
    )
    assert result.ok is True
    assert "X-Signature" in captured_headers
    assert captured_headers["X-Signature"]


def test_deliver_dingtalk_posts_text_message_with_keyword(monkeypatch) -> None:
    captured = {}

    class _Resp:
        status_code = 200

    def _fake_post(url, *, data, headers, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr("app.services.integration_delivery.requests.post", _fake_post)
    result = deliver_dingtalk(
        target="https://oapi.dingtalk.com/robot/send?access_token=token",
        payload={
            "projectName": "Demo",
            "runId": "run-1",
            "status": "FAILED",
            "passRate": "50.00%",
            "failCount": 1,
            "reportUrl": "https://example.test/report",
        },
        rule_json={"keyword": "测试平台"},
        timeout=3,
        max_retries=1,
    )

    assert result.ok is True
    assert captured["url"].startswith("https://oapi.dingtalk.com/robot/send")
    assert captured["headers"]["Content-Type"] == "application/json"
    body = json.loads(captured["data"].decode("utf-8"))
    assert body["msgtype"] == "text"
    assert "测试平台" in body["text"]["content"]
    assert "Demo" in body["text"]["content"]
    assert "FAILED" in body["text"]["content"]


def test_deliver_dingtalk_error_does_not_leak_webhook_token(monkeypatch) -> None:
    target = "https://oapi.dingtalk.com/robot/send?access_token=very-secret-token"

    def _fake_post(*args, **kwargs):
        raise requests.Timeout(f"request timeout for {target}")

    monkeypatch.setattr("app.services.integration_delivery.requests.post", _fake_post)
    result = deliver_dingtalk(
        target=target,
        payload={"runId": "run-1", "status": "FAILED"},
        timeout=1,
        max_retries=1,
    )
    assert result.ok is False
    assert result.error is not None
    assert "very-secret-token" not in result.error


def test_dingtalk_provider_registered_for_im_channel() -> None:
    assert get_notification_provider("IM", "DINGTALK") is deliver_dingtalk


def test_normalize_template_scene_accepts_legacy_alias() -> None:
    assert _normalize_template_scene("WEBHOOK", "WEBHOOK") == "NOTIFICATION_WEBHOOK"
    assert _normalize_template_scene("EMAIL", "EMAIL") == "NOTIFICATION_EMAIL"
    assert _normalize_template_scene("IM", "IM") == "NOTIFICATION_IM"


def test_normalize_template_scene_uses_channel_default_when_empty() -> None:
    assert _normalize_template_scene("WEBHOOK", "") == "NOTIFICATION_WEBHOOK"
    assert _normalize_template_scene("EMAIL", None) == "NOTIFICATION_EMAIL"
