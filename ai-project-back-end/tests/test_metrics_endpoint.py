from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.metrics import render_prometheus_metrics, reset_metrics_for_tests
from app.main import create_app


def test_prometheus_metrics_endpoint_exposes_text_metrics() -> None:
    reset_metrics_for_tests()
    client = TestClient(create_app())

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "weitesting_app_info" in body
    assert "weitesting_process_uptime_seconds" in body
    assert "weitesting_http_requests_total" in body
    assert "weitesting_http_request_duration_seconds_max" in body
    assert "weitesting_http_requests_in_flight" in body
    assert "weitesting_http_request_duration_seconds_sum" in body
    assert "weitesting_http_request_duration_seconds_count" in body
    assert "weitesting_observability_ready" in body


def test_request_metrics_use_route_template_labels() -> None:
    reset_metrics_for_tests()
    client = TestClient(create_app())

    response = client.get(
        "/api/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        headers={
            "X-User-Id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "X-Tenant-Id": "11111111-1111-1111-1111-111111111111",
            "X-Roles": "ADMIN",
        },
    )

    assert response.status_code == 200
    body = render_prometheus_metrics()
    assert 'route="/api/projects/{id}"' in body
    assert "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" not in body
