from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import devops as devops_endpoint
from app.core.database import get_db
from app.services import devops as devops_service


@dataclass
class _DummySession:
    committed: bool = False
    rolled_back: bool = False

    async def commit(self) -> None:
        self.committed = True
        return None

    async def rollback(self) -> None:
        self.rolled_back = True
        return None


def _build_app(db: _DummySession | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(devops_endpoint.router, prefix="/api")
    session = db or _DummySession()

    async def _override_db():
        yield session

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_create_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    db = _DummySession()

    async def _fake_create(db, *, user, project_id, name, provider="github_actions", **kwargs):
        from app.schemas.devops import DevOpsPipelineDetail
        return DevOpsPipelineDetail(
            id="33333333-3333-3333-3333-333333333333",
            projectId=str(project_id),
            name=name,
            provider=provider,
            enabled=True,
            status="IDLE",
            createdAt=1700000000,
            updatedAt=1700000000,
        )

    monkeypatch.setattr(devops_endpoint, "create_pipeline", _fake_create)
    app = _build_app(db)
    client = TestClient(app)
    resp = client.post(
        f"/api/projects/{project_id}/devops/pipelines",
        json={"name": "CI Pipeline", "provider": "github_actions"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "CI Pipeline"
    assert db.committed is True


def test_list_pipelines(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_list(db, *, user, project_id, page, page_size):
        return 0, []

    monkeypatch.setattr(devops_endpoint, "list_pipelines", _fake_list)
    app = _build_app()
    client = TestClient(app)
    resp = client.get(f"/api/projects/{project_id}/devops/pipelines")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 0


def test_trigger_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    pipeline_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_trigger(db, *, user, project_id, pipeline_id, **kwargs):
        from app.schemas.devops import DevOpsRunDetail
        return DevOpsRunDetail(
            id="44444444-4444-4444-4444-444444444444",
            projectId=str(project_id),
            pipelineId=str(pipeline_id),
            status="PENDING",
            triggerType="manual",
            createdAt=1700000000,
            updatedAt=1700000000,
        )

    monkeypatch.setattr(devops_endpoint, "trigger_pipeline", _fake_trigger)
    app = _build_app()
    client = TestClient(app)
    resp = client.post(
        f"/api/projects/{project_id}/devops/pipelines/{pipeline_id}/trigger",
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "PENDING"


def test_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_callback(db, *, project_id, external_run_id, status, **kwargs):
        from app.schemas.devops import DevOpsRunDetail
        return DevOpsRunDetail(
            id="44444444-4444-4444-4444-444444444444",
            projectId=str(project_id),
            pipelineId="33333333-3333-3333-3333-333333333333",
            externalRunId=external_run_id,
            status=status,
            triggerType="ci",
            createdAt=1700000000,
            updatedAt=1700000000,
        )

    monkeypatch.setattr(devops_endpoint, "handle_callback", _fake_callback)
    app = _build_app()
    client = TestClient(app)
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/devops/callback",
        json={"externalRunId": "gh-run-123", "status": "SUCCESS"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "SUCCESS"


def test_callback_forwards_project_and_webhook_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = {}

    async def _fake_callback(db, *, project_id, external_run_id, status, webhook_secret=None, signature=None, raw_body=None, **kwargs):
        from app.schemas.devops import DevOpsRunDetail
        observed["project_id"] = str(project_id)
        observed["webhook_secret"] = webhook_secret
        observed["signature"] = signature
        observed["raw_body"] = raw_body
        return DevOpsRunDetail(
            id="44444444-4444-4444-4444-444444444444",
            projectId=str(project_id),
            pipelineId="33333333-3333-3333-3333-333333333333",
            externalRunId=external_run_id,
            status=status,
            triggerType="ci",
            createdAt=1700000000,
            updatedAt=1700000000,
        )

    monkeypatch.setattr(devops_endpoint, "handle_callback", _fake_callback)
    app = _build_app()
    client = TestClient(app)
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/devops/callback",
        headers={
            "X-Webhook-Secret": "secret-1",
            "X-Hub-Signature-256": "sha256=abc",
        },
        json={"externalRunId": "gh-run-123", "status": "SUCCESS"},
    )
    assert resp.status_code == 200
    assert observed["project_id"] == "22222222-2222-2222-2222-222222222222"
    assert observed["webhook_secret"] == "secret-1"
    assert observed["signature"] == "sha256=abc"
    assert b"gh-run-123" in observed["raw_body"]


def test_jenkins_job_path_escapes_nested_jobs() -> None:
    from app.services.devops import _jenkins_job_path

    assert _jenkins_job_path("folder/My Job") == "job/folder/job/My%20Job"


@pytest.mark.anyio
async def test_create_pipeline_writes_devops_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    project = SimpleNamespace(id=project_id, tenant_id=tenant_id, owner_id=user_id)
    calls: list[dict] = []

    class _Db:
        def __init__(self) -> None:
            self.added = []
            self.flushed = False

        async def scalar(self, stmt):
            return project

        def add(self, row):
            if row.id is None:
                row.id = uuid.UUID("33333333-3333-3333-3333-333333333333")
            if row.enabled is None:
                row.enabled = True
            if row.status is None:
                row.status = "IDLE"
            now = datetime.fromtimestamp(1700000000)
            row.created_at = now
            row.updated_at = now
            self.added.append(row)

        async def flush(self):
            self.flushed = True

    async def _fake_audit(_db, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(devops_service, "create_audit_log", _fake_audit)
    db = _Db()

    detail = await devops_service.create_pipeline(
        db,
        user=user,
        project_id=project_id,
        name="WeiTesting Jenkins Smoke",
        provider="jenkins",
        workflow_file="weitesting-smoke",
        config={"baseUrl": "https://jenkins.evanshine.me", "jobName": "weitesting-smoke"},
    )

    assert detail.name == "WeiTesting Jenkins Smoke"
    assert db.flushed is True
    assert calls
    audit = calls[0]
    assert audit["module"] == "DEVOPS"
    assert audit["action"] == "CREATE_DEVOPS_PIPELINE"
    assert audit["resource_type"] == "devops_pipeline"
    assert audit["project_id"] == project_id


def test_pipeline_detail_masks_sensitive_config() -> None:
    from datetime import datetime
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import _to_pipeline_detail

    row = DevOpsPipeline(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        name="CI",
        provider="github_actions",
        config_json={"github_token": "plain-token", "nested": {"api_key": "plain-key"}, "branch": "main"},
        enabled=True,
        status="IDLE",
        created_at=datetime.fromtimestamp(1700000000),
        updated_at=datetime.fromtimestamp(1700000000),
    )

    detail = _to_pipeline_detail(row)

    assert detail.config == {
        "github_token": "***REDACTED***",
        "nested": {"api_key": "***REDACTED***"},
        "branch": "main",
    }


def test_validate_pipeline_trigger_config_github_missing_items() -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import validate_pipeline_trigger_config

    pipeline = DevOpsPipeline(
        provider="github_actions",
        repo_full_name=None,
        workflow_file=None,
        config_json={},
    )

    diagnostics = validate_pipeline_trigger_config(pipeline)

    assert diagnostics.ok is False
    assert set(diagnostics.missing) == {"repoFullName", "workflowFile", "config.github_token"}


def test_trigger_github_actions_sends_ref_inputs_and_external_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import _trigger_github_actions

    captured: dict = {}

    class _Resp:
        status_code = 204
        text = ""

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr("app.services.devops.http_requests.post", _fake_post)
    pipeline = DevOpsPipeline(
        provider="github_actions",
        repo_full_name="owner/repo",
        workflow_file="ci.yml",
        config_json={"github_token": "ghs_test_token"},
    )

    ok, error_message, _ = _trigger_github_actions(
        pipeline=pipeline,
        branch=None,
        params={"k": "v"},
        external_run_id="ext-123",
    )

    assert ok is True
    assert error_message is None
    assert captured["url"] == "https://api.github.com/repos/owner/repo/actions/workflows/ci.yml/dispatches"
    assert captured["json"]["ref"] == "main"
    assert captured["json"]["inputs"]["k"] == "v"
    assert captured["json"]["inputs"]["weitestingExternalRunId"] == "ext-123"


def test_trigger_github_actions_accepts_frontend_camel_case_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import _trigger_github_actions, validate_pipeline_trigger_config

    captured: dict = {}

    class _Resp:
        status_code = 204
        text = ""

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["headers"] = headers
        captured["json"] = json
        return _Resp()

    monkeypatch.setattr("app.services.devops.http_requests.post", _fake_post)
    pipeline = DevOpsPipeline(
        provider="github_actions",
        repo_full_name="owner/repo",
        workflow_file="ci.yml",
        config_json={"githubToken": "ghs_frontend_token", "defaultBranch": "release"},
    )

    diagnostics = validate_pipeline_trigger_config(pipeline)
    ok, error_message, _ = _trigger_github_actions(
        pipeline=pipeline,
        branch=None,
        params=None,
        external_run_id="ext-frontend-gh",
    )

    assert diagnostics.ok is True
    assert ok is True
    assert error_message is None
    assert captured["headers"]["Authorization"] == "Bearer ghs_frontend_token"
    assert captured["json"]["ref"] == "release"


def test_trigger_jenkins_uses_nested_job_path_and_auth_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import _trigger_jenkins

    captured: dict = {}

    class _Resp:
        status_code = 201
        text = ""
        headers = {"Location": "https://jenkins.example/queue/item/1/"}

    def _fake_post(url, params=None, headers=None, auth=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["auth"] = auth
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr("app.services.devops.http_requests.post", _fake_post)
    pipeline = DevOpsPipeline(
        provider="jenkins",
        workflow_file="folder/My Job",
        config_json={
            "jenkins_url": "https://jenkins.example",
            "username": "ci-user",
            "api_token": "secret-api-token",
            "crumb": "crumb-123",
            "trigger_token": "trig-abc",
        },
    )

    ok, error_message, log_url = _trigger_jenkins(
        pipeline=pipeline,
        params={"foo": "bar"},
        external_run_id="ext-456",
    )

    assert ok is True
    assert error_message is None
    assert log_url == "https://jenkins.example/queue/item/1/"
    assert captured["url"] == "https://jenkins.example/job/folder/job/My%20Job/buildWithParameters"
    assert captured["params"]["foo"] == "bar"
    assert captured["params"]["token"] == "trig-abc"
    assert captured["params"]["WEITESTING_EXTERNAL_RUN_ID"] == "ext-456"
    assert captured["headers"] == {"Jenkins-Crumb": "crumb-123"}
    assert captured["auth"] == ("ci-user", "secret-api-token")


def test_trigger_jenkins_accepts_frontend_camel_case_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import _trigger_jenkins, validate_pipeline_trigger_config

    captured: dict = {}

    class _Resp:
        status_code = 201
        text = ""
        headers = {"Location": "https://jenkins.example/queue/item/2/"}

    def _fake_post(url, params=None, headers=None, auth=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["auth"] = auth
        return _Resp()

    monkeypatch.setattr("app.services.devops.http_requests.post", _fake_post)
    pipeline = DevOpsPipeline(
        provider="jenkins",
        config_json={
            "baseUrl": "https://jenkins.example",
            "jobName": "folder/Frontend Job",
            "username": "ci-user",
            "apiToken": "frontend-api-token",
            "crumb": "frontend-crumb",
            "triggerToken": "frontend-trigger-token",
        },
    )

    diagnostics = validate_pipeline_trigger_config(pipeline)
    ok, error_message, log_url = _trigger_jenkins(
        pipeline=pipeline,
        params={},
        external_run_id="ext-frontend-jenkins",
    )

    assert diagnostics.ok is True
    assert ok is True
    assert error_message is None
    assert log_url == "https://jenkins.example/queue/item/2/"
    assert captured["url"] == "https://jenkins.example/job/folder/job/Frontend%20Job/buildWithParameters"
    assert captured["params"]["token"] == "frontend-trigger-token"
    assert captured["params"]["WEITESTING_EXTERNAL_RUN_ID"] == "ext-frontend-jenkins"
    assert captured["auth"] == ("ci-user", "frontend-api-token")


def test_trigger_jenkins_fetches_crumb_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import _trigger_jenkins

    captured: dict = {}

    class _CrumbResp:
        status_code = 200
        text = ""

        def json(self):
            return {"crumbRequestField": "Jenkins-Crumb", "crumb": "auto-crumb"}

    class _BuildResp:
        status_code = 201
        text = ""
        headers = {"Location": "https://jenkins.example/queue/item/3/"}

    class _Session:
        def get(self, url, auth=None, timeout=None):
            captured["crumbUrl"] = url
            captured["crumbAuth"] = auth
            captured["crumbTimeout"] = timeout
            return _CrumbResp()

        def post(self, url, params=None, headers=None, auth=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["auth"] = auth
            return _BuildResp()

    monkeypatch.setattr("app.services.devops.http_requests.Session", lambda: _Session())
    pipeline = DevOpsPipeline(
        provider="jenkins",
        config_json={
            "baseUrl": "https://jenkins.example",
            "jobName": "Smoke",
            "username": "ci-user",
            "apiToken": "frontend-api-token",
        },
    )

    ok, error_message, log_url = _trigger_jenkins(
        pipeline=pipeline,
        params={},
        external_run_id="ext-auto-crumb",
    )

    assert ok is True
    assert error_message is None
    assert log_url == "https://jenkins.example/queue/item/3/"
    assert captured["crumbUrl"] == "https://jenkins.example/crumbIssuer/api/json"
    assert captured["crumbAuth"] == ("ci-user", "frontend-api-token")
    assert captured["headers"] == {"Jenkins-Crumb": "auto-crumb"}
    assert captured["auth"] == ("ci-user", "frontend-api-token")


def test_trigger_jenkins_falls_back_to_build_for_non_parameterized_job(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import _trigger_jenkins

    calls: list[str] = []

    class _CrumbResp:
        status_code = 200
        text = ""

        def json(self):
            return {"crumbRequestField": "Jenkins-Crumb", "crumb": "auto-crumb"}

    class _NotParameterizedResp:
        status_code = 400
        text = "weitesting-smoke is not parameterized"
        headers = {}

    class _BuildResp:
        status_code = 201
        text = ""
        headers = {"Location": "https://jenkins.example/queue/item/4/"}

    class _Session:
        def get(self, url, auth=None, timeout=None):
            return _CrumbResp()

        def post(self, url, params=None, headers=None, auth=None, timeout=None):
            calls.append(url)
            if url.endswith("/buildWithParameters"):
                return _NotParameterizedResp()
            return _BuildResp()

    monkeypatch.setattr("app.services.devops.http_requests.Session", lambda: _Session())
    pipeline = DevOpsPipeline(
        provider="jenkins",
        config_json={
            "baseUrl": "https://jenkins.example",
            "jobName": "Smoke",
            "username": "ci-user",
            "apiToken": "frontend-api-token",
        },
    )

    ok, error_message, log_url = _trigger_jenkins(
        pipeline=pipeline,
        params={"purpose": "acceptance-smoke"},
        external_run_id="ext-non-parameterized",
    )

    assert ok is True
    assert error_message is None
    assert log_url == "https://jenkins.example/queue/item/4/"
    assert calls == [
        "https://jenkins.example/job/Smoke/buildWithParameters",
        "https://jenkins.example/job/Smoke/build",
    ]


def test_trigger_error_message_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import _trigger_github_actions

    class _Resp:
        status_code = 401
        text = "bad token ghs_ultra_secret_token and api_token=very_secret"

    def _fake_post(*args, **kwargs):
        return _Resp()

    monkeypatch.setattr("app.services.devops.http_requests.post", _fake_post)
    pipeline = DevOpsPipeline(
        provider="github_actions",
        repo_full_name="owner/repo",
        workflow_file="ci.yml",
        config_json={"github_token": "ghs_ultra_secret_token"},
    )

    ok, error_message, _ = _trigger_github_actions(
        pipeline=pipeline,
        branch="main",
        params=None,
        external_run_id="ext-789",
    )

    assert ok is False
    assert error_message is not None
    assert "ghs_ultra_secret_token" not in error_message
    assert "very_secret" not in error_message


def test_validate_pipeline_trigger_config_jenkins_missing_items() -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import validate_pipeline_trigger_config

    pipeline = DevOpsPipeline(
        provider="jenkins",
        repo_full_name=None,
        workflow_file=None,
        config_json={},
    )

    diagnostics = validate_pipeline_trigger_config(pipeline)

    assert diagnostics.ok is False
    assert set(diagnostics.missing) == {"config.base_url", "config.job_name|workflowFile"}


def test_trigger_jenkins_error_message_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.devops_pipeline import DevOpsPipeline
    from app.services.devops import _trigger_jenkins

    class _Resp:
        status_code = 403
        text = "invalid token=jenkins_token_123 and secret=abc123"
        headers = {}

    def _fake_post(*args, **kwargs):
        return _Resp()

    monkeypatch.setattr("app.services.devops.http_requests.post", _fake_post)
    pipeline = DevOpsPipeline(
        provider="jenkins",
        workflow_file="job-1",
        config_json={"jenkins_url": "https://jenkins.example", "trigger_token": "jenkins_token_123"},
    )

    ok, error_message, _ = _trigger_jenkins(
        pipeline=pipeline,
        params={},
        external_run_id="ext-jenkins-1",
    )

    assert ok is False
    assert error_message is not None
    assert "jenkins_token_123" not in error_message
    assert "abc123" not in error_message
