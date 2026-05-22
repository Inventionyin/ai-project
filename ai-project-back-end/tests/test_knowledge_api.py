from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import anyio
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import knowledge as knowledge_endpoint
from app.core.database import get_db
from app.models.enums import ProjectRole
from app.models.project import Project
from app.schemas.knowledge import RecommendationEvaluateResponse, RetrospectiveRecordCreateRequest
from app.services import knowledge as knowledge_service


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(knowledge_endpoint.router, prefix="/api")

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


def _retrospective_detail(project_id: uuid.UUID, record_id: uuid.UUID) -> dict:
    now = int(datetime.now(timezone.utc).timestamp())
    return {
        "id": str(record_id),
        "projectId": str(project_id),
        "title": "登录链路发布回归复盘",
        "sourceType": "PRD",
        "status": "DRAFT",
        "problemSummary": "预发布发现登录态丢失",
        "rootCause": "网关缓存键未包含租户维度",
        "decision": "回滚并补充缓存键策略",
        "actionItems": "补充回归用例并加告警",
        "createdBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "updatedBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "createdAt": now,
        "updatedAt": now,
    }


def test_retrospective_create_and_list_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    record_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_create(db, *, user, project_id, payload):
        assert isinstance(payload, RetrospectiveRecordCreateRequest)
        return _retrospective_detail(project_id, record_id)

    async def _fake_list(db, *, user, project_id, page, page_size, source_type, status):
        assert page == 1
        assert page_size == 20
        assert source_type == "PRD"
        assert status == "DRAFT"
        return 1, [_retrospective_detail(project_id, record_id)]

    monkeypatch.setattr(knowledge_endpoint, "create_retrospective_record", _fake_create)
    monkeypatch.setattr(knowledge_endpoint, "list_retrospective_records", _fake_list)

    client = TestClient(_build_app())
    create_resp = client.post(
        f"/api/projects/{project_id}/knowledge/retrospectives",
        json={
            "title": "登录链路发布回归复盘",
            "sourceType": "PRD",
            "problemSummary": "预发布发现登录态丢失",
            "rootCause": "网关缓存键未包含租户维度",
            "decision": "回滚并补充缓存键策略",
            "actionItems": "补充回归用例并加告警",
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["id"] == str(record_id)

    list_resp = client.get(f"/api/projects/{project_id}/knowledge/retrospectives?page=1&pageSize=20&sourceType=PRD&status=DRAFT")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["id"] == str(record_id)


@dataclass
class _ScalarResult:
    value: object

    def scalar_one_or_none(self):
        return self.value


class _PermissionDeniedDb:
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
            return _ScalarResult(None)
        return _ScalarResult(None)


def test_retrospective_list_permission_denied() -> None:
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )
    with pytest.raises(HTTPException) as exc:
        anyio.run(
            lambda: knowledge_service.list_retrospective_records(
                _PermissionDeniedDb(),
                user=user,
                project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                page=1,
                page_size=20,
                source_type=None,
                status=None,
            )
        )
    assert exc.value.status_code == 403


class _NotFoundDb:
    def __init__(self) -> None:
        self._project_called = False

    async def scalar(self, stmt):
        if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Project:
            self._project_called = True
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


def test_retrospective_get_404() -> None:
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )
    with pytest.raises(HTTPException) as exc:
        anyio.run(
            lambda: knowledge_service.get_retrospective_record(
                _NotFoundDb(),
                user=user,
                project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                record_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            )
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "Retrospective record not found"


def test_recommendations_evaluate_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_evaluate(db, *, user, project_id, payload):
        assert payload.targetType == "RETROSPECTIVE"
        assert payload.targetId == "33333333-3333-3333-3333-333333333333"
        return RecommendationEvaluateResponse(
            targetType="RETROSPECTIVE",
            targetId=payload.targetId,
            recommendations=[
                {
                    "id": "44444444-4444-4444-4444-444444444444",
                    "content": "补充登录链路租户隔离回归用例",
                    "score": 0.92,
                    "type": "TESTCASE",
                    "status": "PENDING",
                }
            ],
        )

    monkeypatch.setattr(knowledge_endpoint, "evaluate_recommendations", _fake_evaluate)
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/knowledge/recommendations/evaluate",
        json={"targetType": "RETROSPECTIVE", "targetId": "33333333-3333-3333-3333-333333333333", "topK": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["targetType"] == "RETROSPECTIVE"
    assert body["data"]["recommendations"][0]["score"] == 0.92


def test_retrospective_draft_from_run_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    run_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
    record_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_create_from_run(db, *, user, project_id, run_id):
        assert run_id == uuid.UUID("88888888-8888-8888-8888-888888888888")
        payload = _retrospective_detail(project_id, record_id)
        payload["sourceType"] = "RUN"
        payload["problemSummary"] = "Run 执行统计：total=5, passed=3, failed=1, skipped=1"
        return payload

    monkeypatch.setattr(knowledge_endpoint, "create_retrospective_draft_from_run", _fake_create_from_run)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/knowledge/retrospectives/draft-from-run",
        json={"runId": str(run_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["sourceType"] == "RUN"
    assert "total=5" in body["data"]["problemSummary"]


def test_update_recommendation_status_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    recommendation_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    async def _fake_update_status(db, *, user, project_id, recommendation_id, status):
        assert status == "ADOPTED"
        return {
            "id": str(recommendation_id),
            "content": "补充登录链路租户隔离回归用例",
            "score": 0.92,
            "type": "TESTCASE",
            "status": "ADOPTED",
        }

    monkeypatch.setattr(knowledge_endpoint, "update_recommendation_status", _fake_update_status)
    client = TestClient(_build_app())
    resp = client.put(
        f"/api/projects/{project_id}/knowledge/recommendations/{recommendation_id}/status",
        json={"status": "ADOPTED"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] == str(recommendation_id)
    assert body["data"]["status"] == "ADOPTED"


def test_update_recommendation_status_invalid_status(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    recommendation_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    async def _fake_update_status_invalid(db, *, user, project_id, recommendation_id, status):
        raise HTTPException(status_code=400, detail="invalid_recommendation_status")

    monkeypatch.setattr(knowledge_endpoint, "update_recommendation_status", _fake_update_status_invalid)
    client = TestClient(_build_app())
    resp = client.put(
        f"/api/projects/{project_id}/knowledge/recommendations/{recommendation_id}/status",
        json={"status": "UNKNOWN"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_recommendation_status"
