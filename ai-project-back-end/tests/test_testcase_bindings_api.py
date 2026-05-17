from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import testcase_bindings as testcase_bindings_endpoint
from app.core.database import get_db
from app.services import testcase_binding as testcase_binding_service


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(testcase_bindings_endpoint.router, prefix="/api")

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


def _binding(**overrides):
    data = {
        "id": uuid.UUID("bbbbbbbb-2222-2222-2222-bbbbbbbbbbbb"),
        "project_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "testcase_id": uuid.UUID("cccccccc-3333-3333-3333-cccccccccccc"),
        "name": "登录接口-主路径",
        "dataset_id": None,
        "api_target_id": None,
        "request_id": None,
        "collection_id": None,
        "link_type": "API_TARGET",
        "source_type": "MANUAL",
        "assert_summary": "断言状态码 200",
        "last_run_status": "PASSED",
        "last_run_at": datetime.fromtimestamp(1710000500),
        "params_json": {},
        "priority": 100,
        "enabled": True,
        "version": 2,
        "updated_at": datetime.fromtimestamp(1710000600),
        "created_at": datetime.fromtimestamp(1710000400),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_list_bindings_by_request_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    request_id = uuid.UUID("aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa")

    async def _fake_list_by_request(db, *, user, project_id, request_id):
        return [_binding(request_id=request_id, link_type="REQUEST")]

    monkeypatch.setattr(testcase_bindings_endpoint, "list_testcase_bindings_by_request", _fake_list_by_request)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/requests/{request_id}/bindings")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data[0]["linkType"] == "REQUEST"
    assert data[0]["requestId"] == str(request_id)
    assert data[0]["lastRunStatus"] == "PASSED"


def test_list_bindings_by_collection_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    collection_id = uuid.UUID("dddddddd-4444-4444-4444-dddddddddddd")

    async def _fake_list_by_collection(db, *, user, project_id, collection_id):
        return [_binding(collection_id=collection_id, link_type="COLLECTION", request_id=None)]

    monkeypatch.setattr(testcase_bindings_endpoint, "list_testcase_bindings_by_collection", _fake_list_by_collection)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/collections/{collection_id}/bindings")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data[0]["linkType"] == "COLLECTION"
    assert data[0]["collectionId"] == str(collection_id)


def test_create_binding_accepts_request_link_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    testcase_id = uuid.UUID("cccccccc-3333-3333-3333-cccccccccccc")
    request_id = uuid.UUID("aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa")

    async def _fake_create(db, *, user, testcase_id, payload):
        assert payload.requestId == str(request_id)
        assert payload.linkType == "REQUEST"
        assert payload.sourceType == "AI"
        assert payload.assertSummary == "状态码为 200"
        return _binding(testcase_id=testcase_id, request_id=request_id, link_type="REQUEST", source_type="AI", assert_summary="状态码为 200")

    monkeypatch.setattr(testcase_bindings_endpoint, "create_testcase_binding", _fake_create)
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/testcases/{testcase_id}/bindings",
        json={
            "name": "登录接口-主路径",
            "requestId": str(request_id),
            "linkType": "REQUEST",
            "sourceType": "AI",
            "assertSummary": "状态码为 200",
            "params": {},
            "priority": 100,
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["requestId"] == str(request_id)
    assert data["linkType"] == "REQUEST"
    assert data["assertSummary"] == "状态码为 200"


def test_update_binding_accepts_collection_link_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    binding_id = uuid.UUID("bbbbbbbb-2222-2222-2222-bbbbbbbbbbbb")
    collection_id = uuid.UUID("dddddddd-4444-4444-4444-dddddddddddd")

    async def _fake_update(db, *, user, binding_id, payload):
        assert payload.collectionId == str(collection_id)
        assert payload.linkType == "COLLECTION"
        return _binding(id=binding_id, collection_id=collection_id, link_type="COLLECTION", version=3)

    monkeypatch.setattr(testcase_bindings_endpoint, "update_testcase_binding", _fake_update)
    client = TestClient(_build_app())
    resp = client.put(
        f"/api/testcase-bindings/{binding_id}",
        json={
            "name": "集合级回归",
            "collectionId": str(collection_id),
            "linkType": "COLLECTION",
            "sourceType": "MANUAL",
            "assertSummary": "",
            "params": {},
            "priority": 100,
            "enabled": True,
            "version": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["collectionId"] == str(collection_id)
    assert data["linkType"] == "COLLECTION"
    assert data["version"] == 3


def test_create_binding_rejects_invalid_link_type_before_service() -> None:
    testcase_id = uuid.UUID("cccccccc-3333-3333-3333-cccccccccccc")
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/testcases/{testcase_id}/bindings",
        json={
            "name": "非法类型",
            "linkType": "BROKEN",
            "sourceType": "MANUAL",
            "assertSummary": "",
            "params": {},
            "priority": 100,
            "enabled": True,
        },
    )
    assert resp.status_code == 422


def test_create_binding_rejects_too_long_assert_summary_before_service() -> None:
    testcase_id = uuid.UUID("cccccccc-3333-3333-3333-cccccccccccc")
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/testcases/{testcase_id}/bindings",
        json={
            "name": "断言过长",
            "linkType": "API_TARGET",
            "sourceType": "MANUAL",
            "assertSummary": "x" * 256,
            "params": {},
            "priority": 100,
            "enabled": True,
        },
    )
    assert resp.status_code == 422


def test_link_consistency_requires_matching_asset_id() -> None:
    with pytest.raises(HTTPException) as request_exc:
        testcase_binding_service._validate_link_consistency(
            link_type="REQUEST",
            api_target_id=None,
            request=None,
            collection=None,
        )
    assert request_exc.value.status_code == 400
    assert request_exc.value.detail == "request_id_required"

    collection = SimpleNamespace(id=uuid.UUID("dddddddd-4444-4444-4444-dddddddddddd"))
    request = SimpleNamespace(collection_id=uuid.UUID("eeeeeeee-5555-5555-5555-eeeeeeeeeeee"))
    with pytest.raises(HTTPException) as mismatch_exc:
        testcase_binding_service._validate_link_consistency(
            link_type="REQUEST",
            api_target_id=None,
            request=request,
            collection=collection,
        )
    assert mismatch_exc.value.status_code == 400
    assert mismatch_exc.value.detail == "request_not_in_collection"


def test_link_consistency_rejects_mixed_api_target_and_api_asset() -> None:
    request = SimpleNamespace(collection_id=uuid.UUID("dddddddd-4444-4444-4444-dddddddddddd"))
    with pytest.raises(HTTPException) as exc:
        testcase_binding_service._validate_link_consistency(
            link_type="REQUEST",
            api_target_id=uuid.UUID("eeeeeeee-5555-5555-5555-eeeeeeeeeeee"),
            request=request,
            collection=None,
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "api_target_cannot_mix_with_api_asset_link"
