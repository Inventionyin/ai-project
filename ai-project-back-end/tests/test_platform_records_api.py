from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import platform_records as platform_records_endpoint
from app.core.database import get_db
from app.models.enums import ProjectRole
from app.models.project import Project


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(platform_records_endpoint.router, prefix="/api")

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


def test_list_ai_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_list_ai_jobs(db, *, user, project_id, page, page_size):
        assert page == 1
        assert page_size == 20
        return 1, [
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "projectId": str(project_id),
                "jobType": "REQUIREMENT_ANALYSIS",
                "status": "SUCCEEDED",
                "triggerSource": "REQUIREMENTS",
                "summary": "完成需求分析并生成测试点",
                "createdBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "createdAt": 1710000000,
            }
        ]

    monkeypatch.setattr(platform_records_endpoint, "list_ai_job_records", _fake_list_ai_jobs)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/platform/ai-jobs")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["jobType"] == "REQUIREMENT_ANALYSIS"


def test_list_audit_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_list_audit_logs(db, *, user, project_id, page, page_size):
        assert page == 2
        assert page_size == 10
        return 1, [
            {
                "id": "44444444-4444-4444-4444-444444444444",
                "projectId": str(project_id),
                "module": "TESTCASE_BINDING",
                "action": "DELETE",
                "resourceType": "testcase_binding",
                "resourceId": "55555555-5555-5555-5555-555555555555",
                "summary": "删除用例绑定",
                "detail": {"name": "登录冒烟绑定"},
                "userId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "createdAt": 1710001234,
            }
        ]

    monkeypatch.setattr(platform_records_endpoint, "list_audit_logs", _fake_list_audit_logs)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/platform/audit-logs?page=2&pageSize=10")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0
    assert payload["data"]["page"] == 2
    assert payload["data"]["items"][0]["module"] == "TESTCASE_BINDING"


@dataclass
class _ScalarResult:
    value: object

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


@dataclass
class _RowsResult:
    rows: list[object]

    class _Rows:
        def __init__(self, rows: list[object]) -> None:
            self._rows = rows

        def all(self) -> list[object]:
            return self._rows

    def scalars(self):
        return self._Rows(self.rows)


class _ServiceDummySession:
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
        if "count" in text.lower():
            return _ScalarResult(1)
        if "ai_job_records" in text:
            row = SimpleNamespace(
                id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
                project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                job_type="REQUIREMENT_ANALYSIS",
                status="SUCCEEDED",
                trigger_source="REQUIREMENTS",
                summary="完成需求分析并生成测试点",
                created_by=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                created_at=datetime.fromtimestamp(1710000000),
            )
            return _RowsResult([row])
        if "audit_logs" in text:
            row = SimpleNamespace(
                id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
                project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                module="TESTCASE_BINDING",
                action="DELETE",
                resource_type="testcase_binding",
                resource_id="55555555-5555-5555-5555-555555555555",
                summary="删除用例绑定",
                detail_json={"name": "登录冒烟绑定"},
                user_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                created_at=datetime.fromtimestamp(1710001234),
            )
            return _RowsResult([row])
        if "project_members.role" in text:
            return _ScalarResult(ProjectRole.VIEWER)
        return _RowsResult([])


def test_platform_records_endpoint_calls_real_service_logic() -> None:
    app = FastAPI()
    app.include_router(platform_records_endpoint.router, prefix="/api")

    async def _override_db():
        yield _ServiceDummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"VIEWER"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    client = TestClient(app)
    ai_resp = client.get("/api/projects/22222222-2222-2222-2222-222222222222/platform/ai-jobs?page=1&pageSize=20")
    assert ai_resp.status_code == 200
    ai_body = ai_resp.json()
    assert ai_body["data"]["total"] == 1
    assert ai_body["data"]["items"][0]["jobType"] == "REQUIREMENT_ANALYSIS"
    assert ai_body["data"]["items"][0]["createdAt"] == 1710000000

    audit_resp = client.get("/api/projects/22222222-2222-2222-2222-222222222222/platform/audit-logs?page=1&pageSize=20")
    assert audit_resp.status_code == 200
    audit_body = audit_resp.json()
    assert audit_body["data"]["total"] == 1
    assert audit_body["data"]["items"][0]["module"] == "TESTCASE_BINDING"
    assert audit_body["data"]["items"][0]["createdAt"] == 1710001234
