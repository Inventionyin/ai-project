from __future__ import annotations

import json
from io import BytesIO

from app.services.postman_cloud import PostmanCloudClient


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload, ensure_ascii=False).encode("utf-8")


def test_postman_cloud_client_lists_workspace_collections(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["api_key"] = request.headers.get("X-api-key")
        captured["timeout"] = timeout
        return _FakeResponse(
            {
                "collections": [
                    {"id": "local-id", "uid": "123-abc", "name": "支付接口", "updatedAt": "2026-05-26T08:00:00Z"}
                ]
            }
        )

    monkeypatch.setattr("app.services.postman_cloud.urlopen", fake_urlopen)

    items = PostmanCloudClient(api_key="pm_key", workspace_id="ws-1").list_collections()

    assert captured["url"] == "https://api.getpostman.com/collections?workspace=ws-1"
    assert captured["api_key"] == "pm_key"
    assert captured["timeout"] == 30
    assert items == [{"id": "local-id", "uid": "123-abc", "name": "支付接口", "updatedAt": "2026-05-26T08:00:00Z"}]


def test_postman_cloud_client_fetches_collection_by_uid(monkeypatch) -> None:
    captured = {}
    collection = {"info": {"name": "支付接口"}, "item": []}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return _FakeResponse({"collection": collection})

    monkeypatch.setattr("app.services.postman_cloud.urlopen", fake_urlopen)

    result = PostmanCloudClient(api_key="pm_key").get_collection("123-abc")

    assert captured["url"] == "https://api.getpostman.com/collections/123-abc"
    assert result == collection
