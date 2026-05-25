from __future__ import annotations

from fastapi.testclient import TestClient

from helpers import assert_success
from test_project_testcase_suite_e2e import _create_api_testcase, _create_project


def test_collection_request_binding_lifecycle_e2e(
    client: TestClient,
    auth_context: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    project = _create_project(client, auth_headers, auth_context["userId"])
    testcase = _create_api_testcase(client, auth_headers, project["id"])

    collection_resp = client.post(
        "/api/collections",
        headers=auth_headers,
        json={
            "projectId": project["id"],
            "name": "E2E 接口集合",
            "variables": {"baseUrl": "https://example.invalid"},
        },
    )
    assert collection_resp.status_code == 200
    collection = assert_success(collection_resp.json())

    request_resp = client.post(
        f"/api/collections/{collection['id']}/requests",
        headers=auth_headers,
        json={
            "name": "Health API",
            "method": "GET",
            "url": "/health",
            "headers": {},
            "auth": {"type": "none"},
            "body": {},
            "asserts": {"status": 200},
        },
    )
    assert request_resp.status_code == 200
    request = assert_success(request_resp.json())

    create_binding_resp = client.post(
        f"/api/testcases/{testcase['id']}/bindings",
        headers=auth_headers,
        json={
            "name": "Health API 请求绑定",
            "requestId": request["id"],
            "linkType": "REQUEST",
            "sourceType": "MANUAL",
            "assertSummary": "状态码为 200",
            "params": {"baseUrl": "https://example.invalid"},
            "priority": 100,
            "enabled": True,
        },
    )
    assert create_binding_resp.status_code == 200
    binding = assert_success(create_binding_resp.json())
    assert binding["testcaseId"] == testcase["id"]
    assert binding["requestId"] == request["id"]
    assert binding["collectionId"] is None
    assert binding["linkType"] == "REQUEST"
    assert binding["version"] == 1

    request_bindings_resp = client.get(
        f"/api/projects/{project['id']}/requests/{request['id']}/bindings",
        headers=auth_headers,
    )
    request_bindings = assert_success(request_bindings_resp.json())
    assert [item["id"] for item in request_bindings] == [binding["id"]]

    collection_bindings_resp = client.get(
        f"/api/projects/{project['id']}/collections/{collection['id']}/bindings",
        headers=auth_headers,
    )
    collection_bindings = assert_success(collection_bindings_resp.json())
    assert binding["id"] in {item["id"] for item in collection_bindings}

    update_resp = client.put(
        f"/api/testcase-bindings/{binding['id']}",
        headers=auth_headers,
        json={
            "name": "Health API 集合绑定",
            "collectionId": collection["id"],
            "linkType": "COLLECTION",
            "sourceType": "MANUAL",
            "assertSummary": "集合回归通过",
            "params": {},
            "priority": 90,
            "enabled": True,
            "version": binding["version"],
        },
    )
    assert update_resp.status_code == 200
    updated = assert_success(update_resp.json())
    assert updated["collectionId"] == collection["id"]
    assert updated["requestId"] is None
    assert updated["linkType"] == "COLLECTION"
    assert updated["version"] == binding["version"] + 1

    delete_resp = client.delete(f"/api/testcase-bindings/{binding['id']}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert_success(delete_resp.json())

    after_delete_resp = client.get(
        f"/api/projects/{project['id']}/collections/{collection['id']}/bindings",
        headers=auth_headers,
    )
    assert assert_success(after_delete_resp.json()) == []
