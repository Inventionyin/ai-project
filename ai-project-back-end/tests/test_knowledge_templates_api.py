from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import knowledge as knowledge_endpoint
from app.core.database import get_db
from app.schemas.knowledge import KnowledgeTemplateDetail


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(knowledge_endpoint.templates_router, prefix="/api")

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


def _template_detail(project_id: uuid.UUID, template_id: uuid.UUID) -> KnowledgeTemplateDetail:
    now = int(datetime.now(timezone.utc).timestamp())
    return KnowledgeTemplateDetail(
        id=str(template_id),
        projectId=str(project_id),
        name="默认复盘模板",
        category="GENERAL",
        contentJson={"sections": ["problem", "rootCause", "actionItems"]},
        status="ACTIVE",
        createdBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        updatedBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        createdAt=now,
        updatedAt=now,
    )


def test_knowledge_templates_create_and_list_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    template_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_create(db, *, user, project_id, payload):
        assert payload.name == "默认复盘模板"
        assert payload.category == "GENERAL"
        return _template_detail(project_id, template_id)

    async def _fake_list(db, *, user, project_id, page, page_size, category, status):
        assert page == 1
        assert page_size == 20
        assert category == "GENERAL"
        assert status == "ACTIVE"
        return 1, [_template_detail(project_id, template_id)]

    monkeypatch.setattr(knowledge_endpoint, "create_knowledge_template", _fake_create)
    monkeypatch.setattr(knowledge_endpoint, "list_knowledge_templates", _fake_list)

    client = TestClient(_build_app())
    create_resp = client.post(
        f"/api/projects/{project_id}/knowledge/templates",
        json={
            "name": "默认复盘模板",
            "category": "GENERAL",
            "contentJson": {"sections": ["problem", "rootCause", "actionItems"]},
            "status": "ACTIVE",
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["id"] == str(template_id)

    list_resp = client.get(
        f"/api/projects/{project_id}/knowledge/templates?page=1&pageSize=20&category=GENERAL&status=ACTIVE"
    )
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["id"] == str(template_id)
