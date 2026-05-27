from __future__ import annotations

from app.services import collection as collection_service


class _FakeHttpResponse:
    status = 200

    def __init__(self) -> None:
        self.headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _size: int | None = None) -> bytes:
        return b'{"status":"ok"}'


def test_execute_http_sets_custom_user_agent(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["timeout"] = timeout
        return _FakeHttpResponse()

    monkeypatch.setattr(collection_service, "urlopen", fake_urlopen)

    result = collection_service._execute_http(
        method="GET",
        url="https://api.evanshine.me/health",
        headers={},
        body_bytes=None,
        timeout_sec=15.0,
    )

    assert captured["timeout"] == 15.0
    assert captured["headers"]["user-agent"] == "weitesting-api-debug/1.0"
    assert result.status == 200
    assert result.error is None
    assert result.body == '{"status":"ok"}'
