from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api.deps import CurrentUser
from app.models.enums import CaseRunStatus, JobStatus, ProjectRole, RunStatus, TriggerType
from app.services import run as run_service


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class _CancelRunDb:
    def __init__(self, *, run_obj, project_obj) -> None:
        self.run_obj = run_obj
        self.project_obj = project_obj
        self.executed = []
        self.flushed = False

    async def scalar(self, stmt):
        text = str(stmt)
        if "FROM runs" in text:
            return self.run_obj
        if "FROM projects" in text:
            return self.project_obj
        return None

    async def execute(self, stmt):
        self.executed.append(str(stmt))
        return _Result([])

    async def flush(self):
        self.flushed = True


class _DeleteAllureDb:
    def __init__(self, *, run_obj, project_obj, artifacts):
        self.run_obj = run_obj
        self.project_obj = project_obj
        self.artifacts = artifacts
        self.deleted_rows = []
        self.flushed = False

    async def scalar(self, stmt):
        text = str(stmt)
        if "FROM runs" in text:
            return self.run_obj
        if "FROM projects" in text:
            return self.project_obj
        return None

    async def execute(self, stmt):
        text = str(stmt)
        if "FROM artifacts" in text:
            return _Result(self.artifacts)
        return _Result([])

    async def delete(self, row):
        self.deleted_rows.append(row)

    async def flush(self):
        self.flushed = True


@pytest.mark.anyio
async def test_cancel_run_writes_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    run_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    run_obj = SimpleNamespace(id=run_id, tenant_id=tenant_id, project_id=project_id, status=RunStatus.RUNNING, end_at=None)
    project_obj = SimpleNamespace(id=project_id, tenant_id=tenant_id, owner_id=user_id)
    db = _CancelRunDb(run_obj=run_obj, project_obj=project_obj)
    calls: list[dict] = []

    async def _fake_audit(_db, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    async def _fake_notify(_db, *, run):
        return None

    monkeypatch.setattr(run_service, "create_audit_log", _fake_audit)
    monkeypatch.setattr(run_service, "dispatch_run_terminal_notification", _fake_notify)

    updated = await run_service.cancel_run(db, user=user, run_id=run_id)

    assert updated.status == RunStatus.CANCELED
    assert calls
    audit = calls[0]
    assert audit["action"] == "CANCEL_RUN"
    assert audit["module"] == "RUN"
    assert audit["resource_type"] == "run"
    assert audit["resource_id"] == str(run_id)
    assert audit["detail"]["status"] == RunStatus.CANCELED.value


@pytest.mark.anyio
async def test_delete_allure_report_writes_audit_log(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    run_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    run_obj = SimpleNamespace(
        id=run_id,
        tenant_id=tenant_id,
        project_id=project_id,
        summary_json={"executionResult": {"reportStatus": "READY"}},
    )
    project_obj = SimpleNamespace(id=project_id, tenant_id=tenant_id, owner_id=user_id)
    report_zip = tmp_path / "allure-report.zip"
    report_zip.write_bytes(b"zip")
    report_dir = tmp_path / "allure-report"
    report_dir.mkdir()
    artifact = SimpleNamespace(
        meta_json={"kind": "ALLURE_REPORT"},
        storage_url=str(report_zip),
        type="LOG_BUNDLE",
        created_at=datetime.utcnow(),
    )
    db = _DeleteAllureDb(run_obj=run_obj, project_obj=project_obj, artifacts=[artifact])
    calls: list[dict] = []

    async def _fake_audit(_db, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(run_service, "create_audit_log", _fake_audit)
    monkeypatch.setattr(
        run_service,
        "resolve_run_allure_paths",
        lambda _rid: (tmp_path / "allure-results", report_dir),
    )

    deleted_artifacts, deleted_files, deleted_dirs = await run_service.delete_run_allure_report(db, user=user, run_id=run_id)

    assert deleted_artifacts == 1
    assert deleted_files >= 1
    assert calls
    audit = calls[0]
    assert audit["action"] == "DELETE_ALLURE_REPORT"
    assert audit["detail"]["deletedArtifacts"] == 1
    assert "deletedFiles" in audit["detail"]
    assert "deletedDirs" in audit["detail"]


@pytest.mark.anyio
async def test_ci_trigger_audit_masks_sensitive_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    owner_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    testcase_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    project = SimpleNamespace(
        id=project_id,
        tenant_id=tenant_id,
        owner_id=owner_id,
        ci_token_hash=run_service._hash_ci_token("ci_secret_token"),
        ci_token_hint="ci_x...abcd",
        ci_token_last_used_at=None,
        ci_token_allowed_runner_types=["DEFAULT"],
        ci_token_allowed_testcase_ids=[],
        ci_token_max_testcase_count=None,
    )
    suite = SimpleNamespace(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        tenant_id=tenant_id,
        project_id=project_id,
        config_json={},
        name="ci suite",
    )
    env = None
    captured = {"rows": []}

    class _Db:
        async def scalar(self, stmt):
            text = str(stmt)
            if "FROM projects" in text:
                return project
            if "FROM test_suites" in text:
                return suite
            if "FROM envs" in text:
                return env
            return None

        def add(self, row):
            captured["rows"].append(row)

        async def flush(self):
            return None

        async def execute(self, _stmt):
            testcase_row = (
                testcase_id,
                project_id,
                "TC-001",
                SimpleNamespace(value="HTTP"),
                "GET",
                "/ci",
                {
                    "apiParams": {},
                    "apiHeaders": {},
                    "expectedResult": None,
                    "expectedStatusCode": 200,
                    "preconditions": None,
                    "postconditions": None,
                },
                "content",
            )
            text = str(_stmt)
            if "FROM testcases" in text:
                return _Result([testcase_row])
            return _Result([])

    async def _fake_require_project_write(*_args, **_kwargs):
        return None

    async def _fake_get_or_create_direct_suite(*_args, **_kwargs):
        return suite

    monkeypatch.setattr(run_service, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(run_service, "_get_or_create_direct_suite", _fake_get_or_create_direct_suite)

    db = _Db()
    run = await run_service.create_run_via_ci_token(
        db,
        project_id=project_id,
        ci_token="ci_secret_token",
        env_id=None,
        meta={"api_token": "plain-secret", "nested": {"password": "123456"}},
        concurrency=1,
        stop_on_failure=False,
        items=[{"testcaseId": str(testcase_id), "overrideParams": {}}],
        notify_rule_id=None,
        idempotency_key=None,
    )

    assert run.project_id == project_id
    audit_rows = [r for r in captured["rows"] if getattr(r, "action", None) == "CI_TRIGGER_RUN"]
    assert len(audit_rows) == 1
    detail = dict(audit_rows[0].detail_json or {})
    assert detail["meta"]["api_token"] == "***REDACTED***"
    assert detail["meta"]["nested"]["password"] == "***REDACTED***"

    http_rows = [r for r in captured["rows"] if getattr(r, "action", None) == "CREATE_RUN_FROM_TESTCASES_HTTP"]
    assert len(http_rows) == 1
    http_detail = dict(http_rows[0].detail_json or {})
    assert http_detail["meta"]["api_token"] == "***REDACTED***"
    assert http_detail["meta"]["nested"]["password"] == "***REDACTED***"


@pytest.mark.anyio
async def test_ci_trigger_denied_policy_writes_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    owner_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    testcase_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    project = SimpleNamespace(
        id=project_id,
        tenant_id=tenant_id,
        owner_id=owner_id,
        ci_token_hash=run_service._hash_ci_token("ci_secret_token"),
        ci_token_hint="ci_x...abcd",
        ci_token_last_used_at=None,
        ci_token_allowed_runner_types=["DEFAULT"],
        ci_token_allowed_testcase_ids=[],
        ci_token_max_testcase_count=1,
    )
    suite = SimpleNamespace(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        tenant_id=tenant_id,
        project_id=project_id,
        config_json={},
        name="ci suite",
    )
    env = None
    captured = {"rows": []}

    class _Db:
        async def scalar(self, stmt):
            text = str(stmt)
            if "FROM projects" in text:
                return project
            if "FROM test_suites" in text:
                return suite
            if "FROM envs" in text:
                return env
            return None

        def add(self, row):
            captured["rows"].append(row)

        async def flush(self):
            return None

        async def execute(self, _stmt):
            testcase_row = (
                testcase_id,
                project_id,
                "TC-001",
                SimpleNamespace(value="HTTP"),
                "GET",
                "/ci",
                {
                    "apiParams": {},
                    "apiHeaders": {},
                    "expectedResult": None,
                    "expectedStatusCode": 200,
                    "preconditions": None,
                    "postconditions": None,
                },
                "content",
            )
            text = str(_stmt)
            if "FROM testcases" in text:
                return _Result([testcase_row])
            return _Result([])

    async def _fake_require_project_write(*_args, **_kwargs):
        return None

    async def _fake_get_or_create_direct_suite(*_args, **_kwargs):
        return suite

    monkeypatch.setattr(run_service, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(run_service, "_get_or_create_direct_suite", _fake_get_or_create_direct_suite)

    db = _Db()
    with pytest.raises(run_service.CiTokenPolicyDenied) as exc:
        await run_service.create_run_via_ci_token(
            db,
            project_id=project_id,
            ci_token="ci_secret_token",
            env_id=None,
            meta={"runnerType": "PYTEST_ALLURE"},
            concurrency=1,
            stop_on_failure=False,
            items=[{"testcaseId": str(testcase_id), "overrideParams": {}}],
            notify_rule_id=None,
            idempotency_key=None,
        )

    assert exc.value.detail == "ci_runner_type_not_allowed"
    audit_rows = [r for r in captured["rows"] if getattr(r, "action", None) == "CI_TRIGGER_DENIED"]
    assert len(audit_rows) == 1
    detail = dict(audit_rows[0].detail_json or {})
    assert detail["reason"] == "ci_runner_type_not_allowed"
    assert detail["runnerType"] == "PYTEST_ALLURE"
    assert all(getattr(r, "action", None) != "CI_TRIGGER_RUN" for r in captured["rows"])


@pytest.mark.anyio
async def test_ci_trigger_denied_unknown_runner_type(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    owner_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    testcase_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    project = SimpleNamespace(
        id=project_id,
        tenant_id=tenant_id,
        owner_id=owner_id,
        ci_token_hash=run_service._hash_ci_token("ci_secret_token"),
        ci_token_hint="ci_x...abcd",
        ci_token_last_used_at=None,
        ci_token_allowed_runner_types=["DEFAULT"],
        ci_token_allowed_testcase_ids=[],
        ci_token_max_testcase_count=None,
    )
    suite = SimpleNamespace(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        tenant_id=tenant_id,
        project_id=project_id,
        config_json={},
        name="ci suite",
    )
    env = None
    captured = {"rows": []}

    class _Db:
        async def scalar(self, stmt):
            text = str(stmt)
            if "FROM projects" in text:
                return project
            if "FROM test_suites" in text:
                return suite
            if "FROM envs" in text:
                return env
            return None

        def add(self, row):
            captured["rows"].append(row)

        async def flush(self):
            return None

        async def execute(self, _stmt):
            testcase_row = (
                testcase_id,
                project_id,
                "TC-001",
                SimpleNamespace(value="HTTP"),
                "GET",
                "/ci",
                {
                    "apiParams": {},
                    "apiHeaders": {},
                    "expectedResult": None,
                    "expectedStatusCode": 200,
                    "preconditions": None,
                    "postconditions": None,
                },
                "content",
            )
            text = str(_stmt)
            if "FROM testcases" in text:
                return _Result([testcase_row])
            return _Result([])

    async def _fake_require_project_write(*_args, **_kwargs):
        return None

    async def _fake_get_or_create_direct_suite(*_args, **_kwargs):
        return suite

    monkeypatch.setattr(run_service, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(run_service, "_get_or_create_direct_suite", _fake_get_or_create_direct_suite)

    db = _Db()
    with pytest.raises(run_service.CiTokenPolicyDenied) as exc:
        await run_service.create_run_via_ci_token(
            db,
            project_id=project_id,
            ci_token="ci_secret_token",
            env_id=None,
            meta={"runnerType": "unknown_runner"},
            concurrency=1,
            stop_on_failure=False,
            items=[{"testcaseId": str(testcase_id), "overrideParams": {}}],
            notify_rule_id=None,
            idempotency_key=None,
        )

    assert exc.value.detail == "ci_runner_type_not_allowed"
    audit_rows = [r for r in captured["rows"] if getattr(r, "action", None) == "CI_TRIGGER_DENIED"]
    assert len(audit_rows) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_reason"),
    [
        ("ci_token_expires_at", datetime.utcfromtimestamp(1700000000), "ci_token_expired"),
        ("ci_token_revoked_at", datetime.utcfromtimestamp(1710000000), "ci_token_revoked"),
        ("ci_token_leak_reported_at", datetime.utcfromtimestamp(1710000000), "ci_token_leaked"),
    ],
)
async def test_ci_trigger_denied_lifecycle_writes_audit(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    field_value: datetime,
    expected_reason: str,
) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    owner_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    testcase_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    project_values = {
        "id": project_id,
        "tenant_id": tenant_id,
        "owner_id": owner_id,
        "ci_token_hash": run_service._hash_ci_token("ci_secret_token"),
        "ci_token_hint": "ci_x...abcd",
        "ci_token_last_used_at": None,
        "ci_token_expires_at": None,
        "ci_token_revoked_at": None,
        "ci_token_revoked_by": None,
        "ci_token_revoked_reason": None,
        "ci_token_leak_reported_at": None,
        "ci_token_leak_reported_by": None,
        "ci_token_leak_report_reason": None,
        "ci_token_allowed_runner_types": ["DEFAULT"],
        "ci_token_allowed_testcase_ids": [],
        "ci_token_max_testcase_count": None,
    }
    project_values[field_name] = field_value
    project = SimpleNamespace(**project_values)
    suite = SimpleNamespace(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        tenant_id=tenant_id,
        project_id=project_id,
        config_json={},
        name="ci suite",
    )
    captured = {"rows": []}

    class _Db:
        async def scalar(self, stmt):
            text = str(stmt)
            if "FROM projects" in text:
                return project
            if "FROM test_suites" in text:
                return suite
            return None

        def add(self, row):
            captured["rows"].append(row)

        async def flush(self):
            return None

        async def execute(self, _stmt):
            testcase_row = (
                testcase_id,
                project_id,
                "TC-001",
                SimpleNamespace(value="HTTP"),
                "GET",
                "/ci",
                {
                    "apiParams": {},
                    "apiHeaders": {},
                    "expectedResult": None,
                    "expectedStatusCode": 200,
                    "preconditions": None,
                    "postconditions": None,
                },
                "content",
            )
            if "FROM testcases" in str(_stmt):
                return _Result([testcase_row])
            return _Result([])

    async def _fake_require_project_write(*_args, **_kwargs):
        return None

    async def _fake_get_or_create_direct_suite(*_args, **_kwargs):
        return suite

    monkeypatch.setattr(run_service, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(run_service, "_get_or_create_direct_suite", _fake_get_or_create_direct_suite)

    db = _Db()
    with pytest.raises(run_service.CiTokenPolicyDenied) as exc:
        await run_service.create_run_via_ci_token(
            db,
            project_id=project_id,
            ci_token="ci_secret_token",
            env_id=None,
            meta={"runnerType": "DEFAULT"},
            concurrency=1,
            stop_on_failure=False,
            items=[{"testcaseId": str(testcase_id), "overrideParams": {}}],
            notify_rule_id=None,
            idempotency_key=None,
        )

    assert exc.value.detail == expected_reason
    audit_rows = [r for r in captured["rows"] if getattr(r, "action", None) == "CI_TRIGGER_DENIED"]
    assert len(audit_rows) == 1
    detail = dict(audit_rows[0].detail_json or {})
    assert detail["reason"] == expected_reason
    assert all(getattr(r, "action", None) != "CI_TRIGGER_RUN" for r in captured["rows"])


@pytest.mark.anyio
async def test_update_ci_token_policy_writes_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=tenant_id,
        roles=frozenset({"ADMIN"}),
    )
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    project = SimpleNamespace(
        id=project_id,
        tenant_id=tenant_id,
        owner_id=user.id,
        ci_token_hash=run_service._hash_ci_token("ci_secret_token"),
        ci_token_hint="ci_x...abcd",
        ci_token_allowed_runner_types=None,
        ci_token_allowed_testcase_ids=None,
        ci_token_max_testcase_count=None,
    )
    captured = {"rows": []}

    class _Db:
        async def scalar(self, stmt):
            if "FROM projects" in str(stmt):
                return project
            return None

        def add(self, row):
            captured["rows"].append(row)

        async def flush(self):
            return None

        async def execute(self, _stmt):
            return _Result([])

    async def _fake_require_project_write(*_args, **_kwargs):
        return None

    monkeypatch.setattr(run_service, "_require_project_write", _fake_require_project_write)

    db = _Db()
    updated = await run_service.update_project_ci_token_policy(
        db,
        user=user,
        project_id=project_id,
        policy={
            "allowedRunnerTypes": ["pytest_allure", "unknown"],
            "allowedTestCaseIds": [str(uuid.UUID("55555555-5555-5555-5555-555555555555")), "bad-id"],
            "maxTestCaseCount": 2,
        },
    )

    assert updated.ci_token_allowed_runner_types == ["PYTEST_ALLURE"]
    assert updated.ci_token_allowed_testcase_ids == ["55555555-5555-5555-5555-555555555555"]
    assert updated.ci_token_max_testcase_count == 2
    audit_rows = [r for r in captured["rows"] if getattr(r, "action", None) == "UPDATE_CI_TOKEN_POLICY"]
    assert len(audit_rows) == 1
    detail = dict(audit_rows[0].detail_json or {})
    assert detail["policy"]["allowedRunnerTypes"] == ["PYTEST_ALLURE"]
    assert detail["policy"]["maxTestCaseCount"] == 2
