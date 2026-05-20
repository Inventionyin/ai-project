from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import runs as runs_endpoint
from app.core.database import get_db
from app.models.enums import RunStatus, TriggerType


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(runs_endpoint.router, prefix="/api")

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_ci_token_rotate_status_revoke(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    now = datetime.utcfromtimestamp(1710000000)
    expires_at = datetime.utcfromtimestamp(1893456000)

    async def _fake_rotate(db, *, user, project_id, policy=None, expires_at=None):
        assert policy == {
            "allowedRunnerTypes": ["pytest_allure"],
            "allowedTestCaseIds": ["66666666-6666-6666-6666-666666666666"],
            "maxTestCaseCount": 5,
        }
        assert expires_at == datetime.utcfromtimestamp(1893456000)
        return (
            SimpleNamespace(
                id=project_id,
                ci_token_hash="hash",
                ci_token_hint="ci_x...abcd",
                ci_token_rotated_at=now,
                ci_token_last_used_at=None,
                ci_token_rotated_by=user.id,
                ci_token_expires_at=expires_at,
                ci_token_revoked_at=None,
                ci_token_revoked_by=None,
                ci_token_revoked_reason=None,
                ci_token_leak_reported_at=None,
                ci_token_leak_reported_by=None,
                ci_token_allowed_runner_types=["PYTEST_ALLURE"],
                ci_token_allowed_testcase_ids=["66666666-6666-6666-6666-666666666666"],
                ci_token_max_testcase_count=5,
            ),
            "ci_test_token",
        )

    async def _fake_status(db, *, user, project_id):
        return SimpleNamespace(
            id=project_id,
            ci_token_hash="hash",
            ci_token_hint="ci_x...abcd",
            ci_token_rotated_at=now,
            ci_token_last_used_at=now,
            ci_token_rotated_by=user.id,
            ci_token_expires_at=expires_at,
            ci_token_revoked_at=None,
            ci_token_revoked_by=None,
            ci_token_revoked_reason=None,
            ci_token_leak_reported_at=None,
            ci_token_leak_reported_by=None,
            ci_token_allowed_runner_types=["PYTEST_ALLURE"],
            ci_token_allowed_testcase_ids=["66666666-6666-6666-6666-666666666666"],
            ci_token_max_testcase_count=5,
        )

    async def _fake_revoke(db, *, user, project_id, reason=None):
        assert reason == "manual rotation"
        return SimpleNamespace(
            id=project_id,
            ci_token_hash="hash",
            ci_token_hint="ci_x...abcd",
            ci_token_rotated_at=now,
            ci_token_last_used_at=None,
            ci_token_rotated_by=user.id,
            ci_token_expires_at=expires_at,
            ci_token_revoked_at=now,
            ci_token_revoked_by=user.id,
            ci_token_revoked_reason="manual rotation",
            ci_token_leak_reported_at=None,
            ci_token_leak_reported_by=None,
            ci_token_allowed_runner_types=None,
            ci_token_allowed_testcase_ids=None,
            ci_token_max_testcase_count=None,
        )

    async def _fake_report_leak(db, *, user, project_id, reason=None):
        assert reason == "secret appeared in CI logs"
        return SimpleNamespace(
            id=project_id,
            ci_token_hash="hash",
            ci_token_hint="ci_x...abcd",
            ci_token_rotated_at=now,
            ci_token_last_used_at=None,
            ci_token_rotated_by=user.id,
            ci_token_expires_at=expires_at,
            ci_token_revoked_at=None,
            ci_token_revoked_by=None,
            ci_token_revoked_reason=None,
            ci_token_leak_reported_at=now,
            ci_token_leak_reported_by=user.id,
            ci_token_allowed_runner_types=None,
            ci_token_allowed_testcase_ids=None,
            ci_token_max_testcase_count=None,
        )

    async def _fake_update_policy(db, *, user, project_id, policy):
        assert policy == {
            "allowedRunnerTypes": ["default"],
            "allowedTestCaseIds": [],
            "maxTestCaseCount": 3,
        }
        return SimpleNamespace(
            id=project_id,
            ci_token_hash="hash",
            ci_token_hint="ci_x...abcd",
            ci_token_rotated_at=now,
            ci_token_last_used_at=now,
            ci_token_rotated_by=user.id,
            ci_token_expires_at=expires_at,
            ci_token_revoked_at=None,
            ci_token_revoked_by=None,
            ci_token_revoked_reason=None,
            ci_token_leak_reported_at=None,
            ci_token_leak_reported_by=None,
            ci_token_allowed_runner_types=["DEFAULT"],
            ci_token_allowed_testcase_ids=[],
            ci_token_max_testcase_count=3,
        )

    monkeypatch.setattr(runs_endpoint, "rotate_project_ci_token", _fake_rotate)
    monkeypatch.setattr(runs_endpoint, "get_project_ci_token_status", _fake_status)
    monkeypatch.setattr(runs_endpoint, "revoke_project_ci_token", _fake_revoke)
    monkeypatch.setattr(runs_endpoint, "report_project_ci_token_leak", _fake_report_leak)
    monkeypatch.setattr(runs_endpoint, "update_project_ci_token_policy", _fake_update_policy)

    client = TestClient(_build_app())

    rotate_resp = client.post(
        "/api/runs/ci-token/rotate",
        json={
            "projectId": str(project_id),
            "policy": {
                "allowedRunnerTypes": ["pytest_allure"],
                "allowedTestCaseIds": ["66666666-6666-6666-6666-666666666666"],
                "maxTestCaseCount": 5,
            },
            "expiresAt": 1893456000,
        },
    )
    assert rotate_resp.status_code == 200
    rotate_data = rotate_resp.json()["data"]
    assert rotate_data["projectId"] == str(project_id)
    assert rotate_data["token"] == "ci_test_token"
    assert rotate_data["enabled"] is True
    assert rotate_data["state"] == "active"
    assert rotate_data["expiresAt"] == 1893456000
    assert rotate_data["policy"]["allowedRunnerTypes"] == ["PYTEST_ALLURE"]
    assert rotate_data["policy"]["maxTestCaseCount"] == 5

    status_resp = client.get(f"/api/runs/ci-token/status?projectId={project_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()["data"]
    assert status_data["enabled"] is True
    assert status_data["state"] == "active"
    assert status_data["hint"] == "ci_x...abcd"
    assert status_data["expiresAt"] == 1893456000
    assert status_data["policy"]["allowedTestCaseIds"] == ["66666666-6666-6666-6666-666666666666"]

    policy_resp = client.put(
        "/api/runs/ci-token/policy",
        json={
            "projectId": str(project_id),
            "policy": {"allowedRunnerTypes": ["default"], "allowedTestCaseIds": [], "maxTestCaseCount": 3},
        },
    )
    assert policy_resp.status_code == 200
    policy_data = policy_resp.json()["data"]
    assert "token" not in policy_data
    assert policy_data["enabled"] is True
    assert policy_data["policy"]["allowedRunnerTypes"] == ["DEFAULT"]
    assert policy_data["policy"]["maxTestCaseCount"] == 3

    revoke_resp = client.request("DELETE", "/api/runs/ci-token", json={"projectId": str(project_id), "reason": "manual rotation"})
    assert revoke_resp.status_code == 200
    revoke_data = revoke_resp.json()["data"]
    assert revoke_data["enabled"] is False
    assert revoke_data["state"] == "revoked"
    assert revoke_data["revokedReason"] == "manual rotation"
    assert revoke_data["policy"]["allowedRunnerTypes"] == []

    leak_resp = client.post(
        "/api/runs/ci-token/report-leak",
        json={"projectId": str(project_id), "reason": "secret appeared in CI logs"},
    )
    assert leak_resp.status_code == 200
    leak_data = leak_resp.json()["data"]
    assert leak_data["enabled"] is False
    assert leak_data["state"] == "leaked"
    assert leak_data["leakReportedAt"] == 1710000000


def test_named_ci_tokens_rotate_list_policy_revoke_and_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    token_id = uuid.UUID("77777777-7777-7777-7777-777777777777")
    now = datetime.utcfromtimestamp(1710000000)
    expires_at = datetime.utcfromtimestamp(1893456000)

    def _record(**overrides):
        data = {
            "id": token_id,
            "project_id": project_id,
            "name": "jenkins-main",
            "is_primary": True,
            "token_hint": "ci_x...main",
            "rotated_at": now,
            "last_used_at": None,
            "rotated_by": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            "expires_at": expires_at,
            "revoked_at": None,
            "revoked_by": None,
            "revoked_reason": None,
            "leak_reported_at": None,
            "leak_reported_by": None,
            "leak_report_reason": None,
            "allowed_runner_types": ["PYTEST_ALLURE"],
            "allowed_testcase_ids": [],
            "max_testcase_count": 10,
        }
        data.update(overrides)
        return SimpleNamespace(**data)

    async def _fake_list(db, *, user, project_id):
        return SimpleNamespace(id=project_id), [_record()]

    async def _fake_rotate(db, *, user, project_id, name, primary=False, policy=None, expires_at=None):
        assert name == "Jenkins-Main"
        assert primary is True
        assert policy == {"allowedRunnerTypes": ["pytest_allure"], "allowedTestCaseIds": [], "maxTestCaseCount": 10}
        assert expires_at == datetime.utcfromtimestamp(1893456000)
        return _record(), "ci_named_token"

    async def _fake_policy(db, *, user, project_id, token_id=None, name=None, policy):
        assert token_id == uuid.UUID("77777777-7777-7777-7777-777777777777")
        assert name is None
        assert policy == {"allowedRunnerTypes": ["default"], "allowedTestCaseIds": [], "maxTestCaseCount": 3}
        return _record(allowed_runner_types=["DEFAULT"], max_testcase_count=3)

    async def _fake_revoke(db, *, user, project_id, token_id=None, name=None, reason=None):
        assert name == "jenkins-main"
        assert reason == "rotate credential"
        return _record(revoked_at=now, revoked_by=user.id, revoked_reason="rotate credential", allowed_runner_types=None, max_testcase_count=None)

    async def _fake_leak(db, *, user, project_id, token_id=None, name=None, reason=None):
        assert name == "jenkins-main"
        assert reason == "found in logs"
        return _record(leak_reported_at=now, leak_reported_by=user.id, leak_report_reason="found in logs", allowed_runner_types=None, max_testcase_count=None)

    monkeypatch.setattr(runs_endpoint, "list_project_ci_token_records", _fake_list)
    monkeypatch.setattr(runs_endpoint, "rotate_project_ci_token_record", _fake_rotate)
    monkeypatch.setattr(runs_endpoint, "update_project_ci_token_record_policy", _fake_policy)
    monkeypatch.setattr(runs_endpoint, "revoke_project_ci_token_record", _fake_revoke)
    monkeypatch.setattr(runs_endpoint, "report_project_ci_token_record_leak", _fake_leak)

    client = TestClient(_build_app())

    rotate_resp = client.post(
        "/api/runs/ci-tokens/rotate",
        json={
            "projectId": str(project_id),
            "name": "Jenkins-Main",
            "primary": True,
            "policy": {"allowedRunnerTypes": ["pytest_allure"], "allowedTestCaseIds": [], "maxTestCaseCount": 10},
            "expiresAt": 1893456000,
        },
    )
    assert rotate_resp.status_code == 200
    rotate_data = rotate_resp.json()["data"]
    assert rotate_data["id"] == str(token_id)
    assert rotate_data["name"] == "jenkins-main"
    assert rotate_data["primary"] is True
    assert rotate_data["token"] == "ci_named_token"
    assert rotate_data["state"] == "active"

    list_resp = client.get(f"/api/runs/ci-tokens?projectId={project_id}")
    assert list_resp.status_code == 200
    list_data = list_resp.json()["data"]
    assert list_data["projectId"] == str(project_id)
    assert list_data["tokens"][0]["hint"] == "ci_x...main"

    policy_resp = client.put(
        "/api/runs/ci-tokens/policy",
        json={
            "projectId": str(project_id),
            "tokenId": str(token_id),
            "policy": {"allowedRunnerTypes": ["default"], "allowedTestCaseIds": [], "maxTestCaseCount": 3},
        },
    )
    assert policy_resp.status_code == 200
    assert policy_resp.json()["data"]["policy"]["allowedRunnerTypes"] == ["DEFAULT"]

    revoke_resp = client.request(
        "DELETE",
        "/api/runs/ci-tokens",
        json={"projectId": str(project_id), "name": "jenkins-main", "reason": "rotate credential"},
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["data"]["state"] == "revoked"

    leak_resp = client.post(
        "/api/runs/ci-tokens/report-leak",
        json={"projectId": str(project_id), "name": "jenkins-main", "reason": "found in logs"},
    )
    assert leak_resp.status_code == 200
    assert leak_resp.json()["data"]["state"] == "leaked"


def test_ci_trigger_success_sets_trigger_type_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    run_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    suite_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    env_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    created_at = datetime.utcfromtimestamp(1710000000)

    async def _fake_create_via_ci(
        db,
        *,
        project_id,
        ci_token,
        env_id,
        meta,
        concurrency,
        stop_on_failure,
        items,
        notify_rule_id,
        idempotency_key,
    ):
        assert ci_token == "ci_ok"
        return SimpleNamespace(
            id=run_id,
            tenant_id=tenant_id,
            created_by=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            suite_id=suite_id,
            env_id=env_id,
            status=RunStatus.QUEUED,
            trigger_type=TriggerType.CI,
            summary_json={},
            start_at=created_at,
            created_at=created_at,
        )

    async def _fake_metrics(db, *, run):
        return 0, 1, 0, 0, 0

    monkeypatch.setattr(runs_endpoint, "create_run_via_ci_token", _fake_create_via_ci)
    monkeypatch.setattr(runs_endpoint, "_load_run_case_metrics", _fake_metrics)

    client = TestClient(_build_app())
    resp = client.post(
        "/api/runs/ci-trigger",
        headers={"X-CI-Token": "ci_ok"},
        json={
            "projectId": str(project_id),
            "envId": str(env_id),
            "items": [{"testcaseId": str(uuid.uuid4()), "overrideParams": {}}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["triggerType"] == TriggerType.CI.value


def test_ci_trigger_rejects_invalid_token() -> None:
    client = TestClient(_build_app())
    resp = client.post(
        "/api/runs/ci-trigger",
        json={
            "projectId": str(uuid.uuid4()),
            "items": [{"testcaseId": str(uuid.uuid4()), "overrideParams": {}}],
        },
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid CI token"
