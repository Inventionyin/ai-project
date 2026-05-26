from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import collections as collections_endpoint
from app.core.database import get_db


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
COLLECTION_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
IMPORTED_COLLECTION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
GROUP_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
REQUEST_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(collections_endpoint.router, prefix="/api")

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


def _collection(**overrides):
    data = {
        "id": COLLECTION_ID,
        "project_id": PROJECT_ID,
        "name": "核心接口集合",
        "variables_json": {"baseUrl": "https://api.example.com"},
        "updated_at": datetime.fromtimestamp(1710000000),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _group(**overrides):
    data = {
        "id": GROUP_ID,
        "collection_id": COLLECTION_ID,
        "name": "认证",
        "order": 1,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _request(**overrides):
    data = {
        "id": REQUEST_ID,
        "collection_id": COLLECTION_ID,
        "group_id": GROUP_ID,
        "name": "账号登录",
        "method": "POST",
        "url": "/api/login",
        "headers_json": {"Content-Type": "application/json"},
        "auth_json": {"type": "none"},
        "body_json": {"username": "qa@example.com"},
        "asserts_json": {"status": 200},
        "updated_at": datetime.fromtimestamp(1710000100),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_list_collections_returns_frontend_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_list_collections(db, *, user, project_id, page, page_size):
        assert project_id == PROJECT_ID
        assert page == 2
        assert page_size == 10
        return 1, [(_collection(), 3)]

    monkeypatch.setattr(collections_endpoint, "list_collections", _fake_list_collections)

    client = TestClient(_build_app())
    resp = client.get(
        "/api/collections",
        params={"projectId": str(PROJECT_ID), "page": 2, "pageSize": 10},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["page"] == 2
    assert body["data"]["pageSize"] == 10
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0] == {
        "id": str(COLLECTION_ID),
        "projectId": str(PROJECT_ID),
        "name": "核心接口集合",
        "requestCount": 3,
        "updatedAt": 1710000000,
    }


def test_create_get_update_delete_collection_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"collection": _collection()}

    async def _fake_create_collection(db, *, user, project_id, name, variables):
        assert project_id == PROJECT_ID
        assert name == "核心接口集合"
        assert variables == {"baseUrl": "https://api.example.com"}
        state["collection"] = _collection(name=name, variables_json=variables)
        return state["collection"]

    async def _fake_update_collection(db, *, user, collection_id, name, variables, variables_is_set):
        assert collection_id == COLLECTION_ID
        assert name == "核心接口集合 v2"
        assert variables == {"baseUrl": "https://staging.example.com"}
        assert variables_is_set is True
        state["collection"] = _collection(name="核心接口集合 v2", variables_json=variables)
        return state["collection"]

    async def _fake_delete_collection(db, *, user, collection_id):
        assert collection_id == COLLECTION_ID

    async def _fake_list_groups_and_requests(db, *, user, collection_id):
        return [_group()], [_request()]

    async def _fake_get_collection(db, *, user, collection_id):
        assert collection_id == COLLECTION_ID
        return state["collection"]

    monkeypatch.setattr(collections_endpoint, "create_collection", _fake_create_collection)
    monkeypatch.setattr(collections_endpoint, "update_collection", _fake_update_collection)
    monkeypatch.setattr(collections_endpoint, "delete_collection", _fake_delete_collection)
    monkeypatch.setattr(collections_endpoint, "list_groups_and_requests", _fake_list_groups_and_requests)
    monkeypatch.setattr(collections_endpoint, "get_collection", _fake_get_collection)

    client = TestClient(_build_app())
    created = client.post(
        "/api/collections",
        json={
            "projectId": str(PROJECT_ID),
            "name": "核心接口集合",
            "variables": {"baseUrl": "https://api.example.com"},
        },
    )
    assert created.status_code == 200
    assert created.json()["data"]["groups"][0]["requests"][0]["id"] == str(REQUEST_ID)

    fetched = client.get(f"/api/collections/{COLLECTION_ID}")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["variables"]["baseUrl"] == "https://api.example.com"

    updated = client.put(
        f"/api/collections/{COLLECTION_ID}",
        json={"name": "核心接口集合 v2", "variables": {"baseUrl": "https://staging.example.com"}},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "核心接口集合 v2"

    deleted = client.delete(f"/api/collections/{COLLECTION_ID}")
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {}


def test_create_update_run_export_request_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_create_request(db, *, user, collection_id, group_id, name, method, url, headers, auth, body, asserts):
        assert collection_id == COLLECTION_ID
        assert group_id == GROUP_ID
        assert method == "POST"
        assert url == "/api/login"
        assert headers == {"Content-Type": "application/json"}
        assert body == {"username": "qa@example.com"}
        assert asserts == {"status": 200}
        return _request()

    async def _fake_get_request(db, *, user, collection_id, request_id):
        assert collection_id == COLLECTION_ID
        assert request_id == REQUEST_ID
        return _collection(), _request()

    async def _fake_update_request(db, *, user, collection_id, request_id, group_id, name, method, url, headers, auth, body, asserts):
        assert request_id == REQUEST_ID
        return _request(name=name, method=method, url=url, headers_json=headers, auth_json=auth, body_json=body, asserts_json=asserts)

    async def _fake_run_request_quick(db, *, user, collection_id, request_id, env_id):
        assert collection_id == COLLECTION_ID
        assert request_id == REQUEST_ID
        assert env_id is None
        return {"status": "PASSED", "durationMs": 18}

    async def _fake_export_collection(db, *, user, collection_id, format):
        assert collection_id == COLLECTION_ID
        assert format == "postman"
        return '{"info":{"name":"核心接口集合"}}'

    monkeypatch.setattr(collections_endpoint, "create_request", _fake_create_request)
    monkeypatch.setattr(collections_endpoint, "get_request", _fake_get_request)
    monkeypatch.setattr(collections_endpoint, "update_request", _fake_update_request)
    monkeypatch.setattr(collections_endpoint, "run_request_quick", _fake_run_request_quick)
    monkeypatch.setattr(collections_endpoint, "export_collection", _fake_export_collection)

    client = TestClient(_build_app())
    payload = {
        "groupId": str(GROUP_ID),
        "name": "账号登录",
        "method": "POST",
        "url": "/api/login",
        "headers": {"Content-Type": "application/json"},
        "auth": {"type": "none"},
        "body": {"username": "qa@example.com"},
        "asserts": {"status": 200},
    }

    created = client.post(f"/api/collections/{COLLECTION_ID}/requests", json=payload)
    assert created.status_code == 200
    assert created.json()["data"]["headers"]["Content-Type"] == "application/json"

    fetched = client.get(f"/api/collections/{COLLECTION_ID}/requests/{REQUEST_ID}")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["body"]["username"] == "qa@example.com"

    updated_payload = {**payload, "name": "账号登录 v2", "url": "/api/login-v2"}
    updated = client.put(f"/api/collections/{COLLECTION_ID}/requests/{REQUEST_ID}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "账号登录 v2"
    assert updated.json()["data"]["url"] == "/api/login-v2"

    run = client.post(f"/api/collections/{COLLECTION_ID}/requests/{REQUEST_ID}/run", json={})
    assert run.status_code == 200
    assert run.json()["data"] == {"status": "PASSED", "durationMs": 18}

    exported = client.get(f"/api/collections/{COLLECTION_ID}/export", params={"format": "postman"})
    assert exported.status_code == 200
    assert exported.json()["data"]["content"] == '{"info":{"name":"核心接口集合"}}'


def test_import_collection_returns_new_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    imported = _collection(
        id=IMPORTED_COLLECTION_ID,
        name="导入的 Postman 集合",
        variables_json={"baseUrl": "https://imported.example.com"},
    )
    imported_group = _group(collection_id=IMPORTED_COLLECTION_ID)
    imported_request = _request(collection_id=IMPORTED_COLLECTION_ID, group_id=GROUP_ID)

    async def _fake_import_collection(db, *, user, project_id, format, content):
        assert project_id == PROJECT_ID
        assert format == "postman"
        assert content == '{"info":{"name":"导入的 Postman 集合"}}'
        return imported

    async def _fake_list_groups_and_requests(db, *, user, collection_id):
        assert collection_id == IMPORTED_COLLECTION_ID
        return [imported_group], [imported_request]

    async def _fake_get_collection(db, *, user, collection_id):
        assert collection_id == IMPORTED_COLLECTION_ID
        return imported

    monkeypatch.setattr(collections_endpoint, "import_collection", _fake_import_collection)
    monkeypatch.setattr(collections_endpoint, "list_groups_and_requests", _fake_list_groups_and_requests)
    monkeypatch.setattr(collections_endpoint, "get_collection", _fake_get_collection)

    client = TestClient(_build_app())
    resp = client.post(
        "/api/collections/import",
        json={
            "projectId": str(PROJECT_ID),
            "format": "postman",
            "content": '{"info":{"name":"导入的 Postman 集合"}}',
        },
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == str(IMPORTED_COLLECTION_ID)
    assert data["name"] == "导入的 Postman 集合"
    assert data["groups"][0]["collectionId"] == str(IMPORTED_COLLECTION_ID)
    assert data["groups"][0]["requests"][0]["collectionId"] == str(IMPORTED_COLLECTION_ID)


def test_postman_cloud_list_and_sync_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    imported = _collection(
        id=IMPORTED_COLLECTION_ID,
        name="云端 Postman 集合",
        variables_json={"_postmanSync": {"uid": "123-abc"}},
    )
    imported_request = _request(collection_id=IMPORTED_COLLECTION_ID, group_id=None)

    async def _fake_list_postman_cloud_collections(db, *, user, project_id, api_key, workspace_id):
        assert project_id == PROJECT_ID
        assert api_key == "pm_key"
        assert workspace_id == "ws-1"
        return [{"id": "local-id", "uid": "123-abc", "name": "云端 Postman 集合", "updatedAt": "2026-05-26T08:00:00Z"}]

    async def _fake_sync_postman_cloud_collection(db, *, user, project_id, collection_uid, api_key, workspace_id):
        assert project_id == PROJECT_ID
        assert collection_uid == "123-abc"
        assert api_key == "pm_key"
        assert workspace_id == "ws-1"
        return imported

    async def _fake_list_groups_and_requests(db, *, user, collection_id):
        assert collection_id == IMPORTED_COLLECTION_ID
        return [], [imported_request]

    async def _fake_get_collection(db, *, user, collection_id):
        assert collection_id == IMPORTED_COLLECTION_ID
        return imported

    monkeypatch.setattr(collections_endpoint, "list_postman_cloud_collections", _fake_list_postman_cloud_collections)
    monkeypatch.setattr(collections_endpoint, "sync_postman_cloud_collection", _fake_sync_postman_cloud_collection)
    monkeypatch.setattr(collections_endpoint, "list_groups_and_requests", _fake_list_groups_and_requests)
    monkeypatch.setattr(collections_endpoint, "get_collection", _fake_get_collection)

    client = TestClient(_build_app())
    listed = client.post(
        "/api/collections/postman/cloud/list",
        json={"projectId": str(PROJECT_ID), "apiKey": "pm_key", "workspaceId": "ws-1"},
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["items"][0]["uid"] == "123-abc"

    synced = client.post(
        "/api/collections/postman/cloud/sync",
        json={"projectId": str(PROJECT_ID), "apiKey": "pm_key", "workspaceId": "ws-1", "collectionUid": "123-abc"},
    )
    assert synced.status_code == 200
    assert synced.json()["data"]["postmanUid"] == "123-abc"
    assert synced.json()["data"]["collection"]["id"] == str(IMPORTED_COLLECTION_ID)


def test_run_collection_and_group_reorder_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_run_collection_quick(db, *, user, collection_id, env_id, concurrency, iterations):
        assert collection_id == COLLECTION_ID
        assert env_id == uuid.UUID("77777777-7777-7777-7777-777777777777")
        assert concurrency == 3
        assert iterations == 2
        return {"status": "COMPLETED", "total": 6, "passed": 6}

    async def _fake_reorder_groups(db, *, user, collection_id, items):
        assert collection_id == COLLECTION_ID
        assert items == [(GROUP_ID, 2)]

    async def _fake_list_groups_and_requests(db, *, user, collection_id):
        return [_group(order=2)], []

    monkeypatch.setattr(collections_endpoint, "run_collection_quick", _fake_run_collection_quick)
    monkeypatch.setattr(collections_endpoint, "reorder_groups", _fake_reorder_groups)
    monkeypatch.setattr(collections_endpoint, "list_groups_and_requests", _fake_list_groups_and_requests)

    client = TestClient(_build_app())
    run = client.post(
        f"/api/collections/{COLLECTION_ID}/run",
        json={
            "envId": "77777777-7777-7777-7777-777777777777",
            "concurrency": 3,
            "iterations": 2,
        },
    )
    assert run.status_code == 200
    assert run.json()["data"]["passed"] == 6

    reordered = client.put(
        f"/api/collections/{COLLECTION_ID}/groups",
        json={"groups": [{"id": str(GROUP_ID), "order": 2}]},
    )
    assert reordered.status_code == 200
    assert reordered.json()["data"][0]["order"] == 2


def test_create_request_rejects_missing_url_before_service(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _should_not_call(*args, **kwargs):
        raise AssertionError("create_request should not be called when payload is invalid")

    monkeypatch.setattr(collections_endpoint, "create_request", _should_not_call)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/collections/{COLLECTION_ID}/requests",
        json={"name": "缺少 URL", "method": "GET"},
    )

    assert resp.status_code == 422
