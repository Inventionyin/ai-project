from __future__ import annotations

import uuid
import asyncio
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import integration_issues as integration_issues_endpoint
from app.core.database import get_db
from app.models.enums import ProjectRole
from app.models.enums import RunStatus, TriggerType
from app.models.project import Project
from app.models.run import Run
from app.schemas.integration_issue import IntegrationIssueDetail
from app.schemas.integration_issue import IntegrationIssueCreateRequest
from app.services import integration_issue as integration_issue_service


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(integration_issues_endpoint.router, prefix="/api")

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


def _issue_detail(project_id: uuid.UUID, run_id: uuid.UUID, issue_id: uuid.UUID) -> IntegrationIssueDetail:
    return IntegrationIssueDetail(
        id=str(issue_id),
        runId=str(run_id),
        caseRunId=None,
        provider="JIRA",
        issueKey="JIRA-AB12CD34",
        url="https://jira.local/issues/JIRA-AB12CD34",
        createdAt=1710000000,
    )


def test_integration_issues_create_and_list_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    expected_run_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    issue_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    async def _fake_create(db, *, user, project_id, payload):
        assert payload.provider == "JIRA"
        assert payload.runId == str(expected_run_id)
        return _issue_detail(project_id, expected_run_id, issue_id)

    async def _fake_list(db, *, user, project_id, run_id, case_run_id, provider):
        assert run_id == expected_run_id
        assert provider == "JIRA"
        return [_issue_detail(project_id, expected_run_id, issue_id)]

    monkeypatch.setattr(integration_issues_endpoint, "create_issue_link", _fake_create)
    monkeypatch.setattr(integration_issues_endpoint, "list_issue_links", _fake_list)

    client = TestClient(_build_app())
    create_resp = client.post(
        f"/api/projects/{project_id}/integrations/issues",
        json={
            "provider": "JIRA",
            "runId": str(expected_run_id),
            "title": "支付回调失败",
            "description": "线上复现",
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["id"] == str(issue_id)

    list_resp = client.get(
        f"/api/projects/{project_id}/integrations/issues?runId={expected_run_id}&provider=JIRA"
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["data"][0]["issueKey"] == "JIRA-AB12CD34"


@dataclass
class _ScalarResult:
    value: object

    def scalar_one_or_none(self):
        return self.value


class _ViewerWriteDeniedDb:
    async def scalar(self, stmt):
        if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Project:
            return Project(
                id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                name="proj",
                owner_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            )
        return None

    async def execute(self, stmt):
        text = str(stmt)
        if "project_members.role" in text:
            return _ScalarResult(ProjectRole.VIEWER)
        return _ScalarResult(None)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def flush(self) -> None:
        return None

    def add(self, row) -> None:
        return None


def test_integration_issue_create_forbidden_for_viewer() -> None:
    app = FastAPI()
    app.include_router(integration_issues_endpoint.router, prefix="/api")

    async def _override_db():
        yield _ViewerWriteDeniedDb()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset(),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    client = TestClient(app)
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/issues",
        json={
            "provider": "JIRA",
            "runId": "33333333-3333-3333-3333-333333333333",
            "title": "支付回调失败",
            "description": "线上复现",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Only Owner/Editor can modify this project"


class _CreateIssueDb:
    async def scalar(self, stmt):
        if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Project:
            return Project(
                id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                name="proj",
                owner_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            )
        if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Run:
            return Run(
                id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
                tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                trigger_type=TriggerType.MANUAL,
                status=RunStatus.PASSED,
            )
        return None

    async def execute(self, stmt):
        return _ScalarResult(ProjectRole.EDITOR)

    async def flush(self) -> None:
        return None

    def add(self, row) -> None:
        return None


def test_integration_issue_create_redacts_sensitive_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    user = CurrentUser(
        id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )

    def _provider(_provider: str, **kwargs):
        raise ValueError("token=abc secret=xyz")

    monkeypatch.setattr(integration_issue_service, "resolve_issue_provider", lambda _name: _provider)
    payload = IntegrationIssueCreateRequest(
        provider="JIRA",
        runId="33333333-3333-3333-3333-333333333333",
        title="x",
    )
    async def _run():
        return await integration_issue_service.create_issue_link(
            _CreateIssueDb(),
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
        )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(_run())
    assert exc.value.status_code == 400
    assert exc.value.detail == "issue_provider_error: sensitive value redacted"


def test_integration_issue_create_redacts_provider_config_details(monkeypatch: pytest.MonkeyPatch) -> None:
    user = CurrentUser(
        id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )

    def _provider(_provider: str, **kwargs):
        raise ValueError("jira_missing_base_url")

    monkeypatch.setattr(integration_issue_service, "resolve_issue_provider", lambda _name: _provider)
    payload = IntegrationIssueCreateRequest(
        provider="JIRA",
        runId="33333333-3333-3333-3333-333333333333",
        title="x",
    )

    async def _run():
        return await integration_issue_service.create_issue_link(
            _CreateIssueDb(),
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
        )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(_run())
    assert exc.value.status_code == 400
    assert exc.value.detail == "issue_provider_error: provider config missing or invalid"


def test_integration_issue_create_passes_execute_request_flag_to_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    user = CurrentUser(
        id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )
    observed: dict[str, object] = {}

    def _provider(_provider: str, **kwargs):
        observed.update(kwargs)
        return integration_issue_service.IssueProviderResult(
            issue_key="JIRA-123",
            url="https://jira.example/browse/JIRA-123",
        )

    monkeypatch.setattr(integration_issue_service, "resolve_issue_provider", lambda _name: _provider)
    payload = IntegrationIssueCreateRequest(
        provider="JIRA",
        runId="33333333-3333-3333-3333-333333333333",
        title="真实创建",
        executeRequest=True,
        timeoutSeconds=3.5,
        config={"realCreateEnabled": True},
    )

    async def _run():
        return await integration_issue_service.create_issue_link(
            _CreateIssueDb(),
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
        )

    detail = asyncio.run(_run())
    assert detail.issueKey == "JIRA-123"
    assert observed["execute_request"] is True
    assert observed["timeout"] == 3.5


def test_integration_issue_create_blocks_execute_request_without_config_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = CurrentUser(
        id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )

    def _provider(_provider: str, **kwargs):
        raise AssertionError("provider should not be called when real creation is not configured")

    monkeypatch.setattr(integration_issue_service, "resolve_issue_provider", lambda _name: _provider)
    payload = IntegrationIssueCreateRequest(
        provider="JIRA",
        runId="33333333-3333-3333-3333-333333333333",
        title="真实创建",
        executeRequest=True,
        config={},
    )

    async def _run():
        return await integration_issue_service.create_issue_link(
            _CreateIssueDb(),
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
        )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(_run())
    assert exc.value.status_code == 400
    assert exc.value.detail == "real_issue_creation_not_enabled"
