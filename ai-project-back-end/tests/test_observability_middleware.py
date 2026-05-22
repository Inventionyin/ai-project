from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.observability import mask_sensitive_mapping, mask_sensitive_text


def test_request_id_response_header_present() -> None:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    from app.main import log_requests

    app.middleware("http")(log_requests)

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers["X-Request-Id"]
    assert resp.headers["X-Response-Time-Ms"]


def test_request_id_response_header_is_normalized() -> None:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    from app.main import log_requests

    app.middleware("http")(log_requests)

    client = TestClient(app)
    resp = client.get("/health", headers={"X-Request-Id": "req/with@symbols"})
    assert resp.status_code == 200
    assert resp.headers["X-Request-Id"] == "req-with-symbols"


def test_request_id_is_normalized_and_echoed_back() -> None:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    from app.main import log_requests

    app.middleware("http")(log_requests)

    client = TestClient(app)
    resp = client.get("/health", headers={"X-Request-Id": "  invalid id  "})
    assert resp.status_code == 200
    assert resp.headers["X-Request-Id"] == "invalid-id"


def test_request_id_preserves_valid_identifier() -> None:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    from app.main import log_requests

    app.middleware("http")(log_requests)

    request_id = str(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
    client = TestClient(app)
    resp = client.get("/health", headers={"X-Request-Id": request_id})
    assert resp.status_code == 200
    assert resp.headers["X-Request-Id"] == request_id


def test_mask_sensitive_helpers() -> None:
    assert mask_sensitive_text("Bearer abc.def.ghi") == "Bearer ******"
    data = mask_sensitive_mapping(
        {
            "token": "abc",
            "headers": {"Authorization": "Bearer abc"},
            "nested": [{"password": "secret"}, {"ok": "value"}],
        }
    )
    assert data["token"] == "******"
    assert data["headers"]["Authorization"] == "******"
    assert data["nested"][0]["password"] == "******"
