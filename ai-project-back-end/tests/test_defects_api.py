from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import anyio
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import defects as defects_endpoint
from app.core.database import get_db
from app.schemas.defect import DefectCreateRequest, DefectTransitionRequest
from app.services import defect as defect_service


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(defects_endpoint.router, prefix="/api")

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


def _defect_detail(project_id: uuid.UUID, defect_id: uuid.UUID) -> dict:
    now = int(datetime.now(timezone.utc).timestamp())
    return {
        "id": str(defect_id),
        "projectId": str(project_id),
        "title": "登录页验证码偶现不展示",
        "description": "在低网速下复现",
        "status": "OPEN",
        "severity": "P1",
        "assigneeId": None,
        "reporterId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "createdBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "createdAt": now,
        "updatedAt": now,
    }


def test_defect_endpoints_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    defect_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    assignee_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    async def _fake_create(db, *, user, project_id, payload):
        assert isinstance(payload, DefectCreateRequest)
        return _defect_detail(project_id, defect_id)

    async def _fake_list(db, *, user, project_id, page, page_size, status=None, q=None):
        return 1, [_defect_detail(project_id, defect_id)]

    async def _fake_get(db, *, user, project_id, defect_id):
        return _defect_detail(project_id, defect_id)

    async def _fake_assign(db, *, user, project_id, defect_id, assignee_id, note=None):
        data = _defect_detail(project_id, defect_id)
        data["assigneeId"] = str(assignee_id)
        return data

    async def _fake_transition(db, *, user, project_id, defect_id, payload):
        assert payload.toStatus == "IN_PROGRESS"
        data = _defect_detail(project_id, defect_id)
        data["status"] = "IN_PROGRESS"
        return data

    monkeypatch.setattr(defects_endpoint, "create_defect", _fake_create)
    monkeypatch.setattr(defects_endpoint, "list_defects", _fake_list)
    monkeypatch.setattr(defects_endpoint, "get_defect", _fake_get)
    monkeypatch.setattr(defects_endpoint, "assign_defect", _fake_assign)
    monkeypatch.setattr(defects_endpoint, "transition_defect", _fake_transition)

    client = TestClient(_build_app())
    create_resp = client.post(
        f"/api/projects/{project_id}/defects",
        json={"title": "登录页验证码偶现不展示", "description": "在低网速下复现", "severity": "P1"},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["id"] == str(defect_id)

    list_resp = client.get(f"/api/projects/{project_id}/defects?page=1&pageSize=20")
    assert list_resp.status_code == 200
    assert list_resp.json()["data"]["items"][0]["id"] == str(defect_id)

    get_resp = client.get(f"/api/projects/{project_id}/defects/{defect_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["status"] == "OPEN"

    assign_resp = client.post(
        f"/api/projects/{project_id}/defects/{defect_id}/assign",
        json={"assigneeId": str(assignee_id)},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["data"]["assigneeId"] == str(assignee_id)

    transition_resp = client.post(
        f"/api/projects/{project_id}/defects/{defect_id}/transition",
        json={"toStatus": "IN_PROGRESS"},
    )
    assert transition_resp.status_code == 200
    assert transition_resp.json()["data"]["status"] == "IN_PROGRESS"


def test_transition_rejects_invalid_status_flow() -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    defect_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))

    class _DB:
        async def scalar(self, stmt):
            entity = stmt.column_descriptions[0]["entity"]
            if entity.__name__ == "Project":
                return SimpleNamespace(id=project_id, tenant_id=tenant_id, owner_id=user_id)
            if entity.__name__ == "Defect":
                return SimpleNamespace(
                    id=defect_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    status="OPEN",
                    severity="P2",
                    title="x",
                    description=None,
                    assignee_id=None,
                    reporter_id=user_id,
                    created_by=user_id,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            return None

        async def flush(self):
            return None

        def add(self, row):
            return None

    with pytest.raises(HTTPException) as exc:
        anyio.run(
            lambda: defect_service.transition_defect(
                _DB(),
                user=user,
                project_id=project_id,
                defect_id=defect_id,
                payload=DefectTransitionRequest(toStatus="RESOLVED"),
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "invalid_status_transition"


def test_defect_import_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_import(db, *, user, project_id, payload):
        assert len(payload.items) == 2
        return {
            "total": 2,
            "success": 2,
            "failed": 0,
            "errors": [],
        }

    monkeypatch.setattr(defects_endpoint, "import_defects", _fake_import)
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/defects/import",
        json={
            "items": [
                {
                    "title": "登录按钮偶现无法点击",
                    "description": "iOS Safari 下出现",
                    "severity": "P1",
                    "source": "manual",
                },
                {
                    "title": "订单页渲染报错",
                    "description": "控制台出现 null 引用",
                    "severity": "P0",
                    "runId": "55555555-5555-5555-5555-555555555555",
                },
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["total"] == 2
    assert body["success"] == 2
    assert body["failed"] == 0


def test_defect_clusters_and_risk_hints_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_clusters(db, *, user, project_id):
        return [
            {
                "clusterKey": "login-timeout",
                "count": 3,
                "sampleTitles": ["登录超时", "登录态丢失", "登录页白屏"],
                "rootCauseHint": "可能是网络或依赖服务不稳定",
                "confidence": 0.78,
            }
        ]

    async def _fake_risk_hints(db, *, user, project_id):
        return [
            {
                "defectId": "33333333-3333-3333-3333-333333333333",
                "title": "支付回调偶发失败",
                "status": "OPEN",
                "severity": "P0",
                "updatedAt": int(datetime.now(timezone.utc).timestamp()),
                "riskScore": 8.2,
                "hint": "高优先级且近期活跃，建议优先回归",
            }
        ]

    monkeypatch.setattr(defects_endpoint, "list_defect_clusters", _fake_clusters)
    monkeypatch.setattr(defects_endpoint, "list_defect_risk_hints", _fake_risk_hints)

    client = TestClient(_build_app())
    clusters_resp = client.get(f"/api/projects/{project_id}/defects/clusters")
    assert clusters_resp.status_code == 200
    assert clusters_resp.json()["data"][0]["clusterKey"] == "login-timeout"

    risk_resp = client.get(f"/api/projects/{project_id}/defects/risk-hints")
    assert risk_resp.status_code == 200
    assert risk_resp.json()["data"][0]["status"] == "OPEN"
