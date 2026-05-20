from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_prometheus_metrics_endpoint_exposes_text_metrics() -> None:
    client = TestClient(create_app())

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "weitesting_app_info" in body
    assert "weitesting_process_uptime_seconds" in body
    assert "weitesting_http_requests_total" in body
