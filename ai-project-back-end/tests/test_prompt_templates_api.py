from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import prompt_templates as prompt_templates_endpoint
from app.core.database import get_db
from app.models.enums import ProjectRole
from app.models.project import Project
from app.schemas.prompt_template import PromptTemplateDetail


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(prompt_templates_endpoint.router, prefix="/api")

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


def _template_detail(project_id: uuid.UUID, template_id: uuid.UUID) -> PromptTemplateDetail:
    return PromptTemplateDetail(
        id=str(template_id),
        projectId=str(project_id),
        scene="run_summary",
        name="run_summary_cn",
        version="v1",
        content="run {{runId}} finished",
        variablesJson={"runId": "{{runId}}"},
        isActive=True,
        createdBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        createdAt=1710000000,
    )


def test_prompt_template_create_list_and_activate(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    template_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_create(db, *, user, project_id, payload):
        assert payload.scene == "run_summary"
        assert payload.version == "v1"
        return _template_detail(project_id, template_id)

    async def _fake_list(db, *, user, project_id, scene, name):
        assert scene == "run_summary"
        assert name == "run_summary_cn"
        return [_template_detail(project_id, template_id)]

    async def _fake_activate(db, *, user, project_id, template_id, payload):
        assert payload.isActive is True
        return _template_detail(project_id, template_id)

    async def _fake_governance(db, *, user, project_id):
        return [
            {
                "scene": "run_summary",
                "name": "run_summary_cn",
                "activeVersion": "v1",
                "latestVersion": "v2",
                "versionCount": 2,
                "policy": "SINGLE_ACTIVE",
            }
        ]

    async def _fake_rollback(db, *, user, project_id, payload):
        assert payload.scene == "run_summary"
        assert payload.name == "run_summary_cn"
        assert payload.targetVersion == "v1"
        return {
            "scene": payload.scene,
            "name": payload.name,
            "activeVersion": payload.targetVersion,
            "versionCount": 2,
            "policy": "SINGLE_ACTIVE",
        }

    monkeypatch.setattr(prompt_templates_endpoint, "create_prompt_template", _fake_create)
    monkeypatch.setattr(prompt_templates_endpoint, "list_prompt_templates", _fake_list)
    monkeypatch.setattr(prompt_templates_endpoint, "activate_prompt_template", _fake_activate)
    monkeypatch.setattr(prompt_templates_endpoint, "list_prompt_template_governance", _fake_governance)
    monkeypatch.setattr(prompt_templates_endpoint, "rollback_prompt_template", _fake_rollback)

    client = TestClient(_build_app())
    create_resp = client.post(
        f"/api/projects/{project_id}/prompt-templates",
        json={
            "scene": "run_summary",
            "name": "run_summary_cn",
            "version": "v1",
            "content": "run {{runId}} finished",
            "variablesJson": {"runId": "{{runId}}"},
            "isActive": True,
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["id"] == str(template_id)

    list_resp = client.get(f"/api/projects/{project_id}/prompt-templates?scene=run_summary&name=run_summary_cn")
    assert list_resp.status_code == 200
    assert list_resp.json()["data"][0]["name"] == "run_summary_cn"

    activate_resp = client.post(f"/api/projects/{project_id}/prompt-templates/{template_id}/activate", json={"isActive": True})
    assert activate_resp.status_code == 200
    assert activate_resp.json()["data"]["isActive"] is True

    governance_resp = client.get(f"/api/projects/{project_id}/prompt-templates/governance")
    assert governance_resp.status_code == 200
    assert governance_resp.json()["data"][0]["policy"] == "SINGLE_ACTIVE"

    rollback_resp = client.post(
        f"/api/projects/{project_id}/prompt-templates/rollback",
        json={"scene": "run_summary", "name": "run_summary_cn", "targetVersion": "v1"},
    )
    assert rollback_resp.status_code == 200
    assert rollback_resp.json()["data"]["activeVersion"] == "v1"


def test_prompt_template_rollback_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_rollback_not_found(db, *, user, project_id, payload):
        raise HTTPException(status_code=404, detail="prompt_template_version_not_found")

    monkeypatch.setattr(prompt_templates_endpoint, "rollback_prompt_template", _fake_rollback_not_found)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/prompt-templates/rollback",
        json={"scene": "run_summary", "name": "run_summary_cn", "targetVersion": "v9"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "prompt_template_version_not_found"


def test_prompt_template_rollback_idempotent_when_target_is_active(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_rollback(db, *, user, project_id, payload):
        return {
            "scene": payload.scene,
            "name": payload.name,
            "activeVersion": payload.targetVersion,
            "versionCount": 3,
            "policy": "SINGLE_ACTIVE",
        }

    monkeypatch.setattr(prompt_templates_endpoint, "rollback_prompt_template", _fake_rollback)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/prompt-templates/rollback",
        json={"scene": "run_summary", "name": "run_summary_cn", "targetVersion": "v2"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["activeVersion"] == "v2"


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


def test_prompt_template_create_forbidden_for_viewer() -> None:
    app = FastAPI()
    app.include_router(prompt_templates_endpoint.router, prefix="/api")

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
        "/api/projects/22222222-2222-2222-2222-222222222222/prompt-templates",
        json={
            "scene": "run_summary",
            "name": "run_summary_cn",
            "version": "v1",
            "content": "run {{runId}} finished",
            "variablesJson": {"runId": "{{runId}}"},
            "isActive": True,
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Only Owner/Editor can modify this project"
