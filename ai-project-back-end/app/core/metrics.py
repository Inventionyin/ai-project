from __future__ import annotations

from collections import Counter
import re
import time


_STARTED_AT = time.time()
_REQUEST_TOTAL: Counter[tuple[str, str, str]] = Counter()
_REQUEST_DURATION_SUM: Counter[tuple[str, str]] = Counter()
_REQUEST_DURATION_COUNT: Counter[tuple[str, str]] = Counter()
_REQUEST_DURATION_MAX: Counter[tuple[str, str]] = Counter()
_REQUEST_IN_FLIGHT: Counter[tuple[str, str]] = Counter()
_REQUEST_ERRORS_TOTAL: Counter[tuple[str, str]] = Counter()


_UUID_RE = re.compile(r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)")
_HEX_RE = re.compile(r"/[0-9a-fA-F]{16,}(?=/|$)")
_INT_RE = re.compile(r"/\d{4,}(?=/|$)")


def _normalize_route(path: str) -> str:
    route = path.split("?", 1)[0] or "/"
    route = _UUID_RE.sub("/{id}", route)
    route = _HEX_RE.sub("/{id}", route)
    route = _INT_RE.sub("/{id}", route)
    return route[:160]


def normalize_route_label(path: str) -> str:
    return _normalize_route(path)


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float, route: str | None = None) -> None:
    route = _normalize_route(route or path)
    status_class = f"{int(status_code / 100)}xx"
    key = (method.upper(), route, status_class)
    duration_key = (method.upper(), route)
    _REQUEST_TOTAL[key] += 1
    _REQUEST_DURATION_SUM[duration_key] += duration_seconds
    _REQUEST_DURATION_COUNT[duration_key] += 1
    _REQUEST_DURATION_MAX[duration_key] = max(_REQUEST_DURATION_MAX[duration_key], duration_seconds)
    if status_code >= 500:
        _REQUEST_ERRORS_TOTAL[duration_key] += 1


def increment_in_flight_request(method: str, path: str, route: str | None = None) -> tuple[str, str]:
    key = (method.upper(), _normalize_route(route or path))
    _REQUEST_IN_FLIGHT[key] += 1
    return key


def decrement_in_flight_request(key: tuple[str, str]) -> None:
    _REQUEST_IN_FLIGHT[key] = max(0, _REQUEST_IN_FLIGHT[key] - 1)


def _metric_line(name: str, labels: dict[str, str], value: float | int) -> str:
    label_text = ",".join(f'{key}="{val}"' for key, val in labels.items())
    return f"{name}{{{label_text}}} {value}" if label_text else f"{name} {value}"


def reset_metrics_for_tests() -> None:
    _REQUEST_TOTAL.clear()
    _REQUEST_DURATION_SUM.clear()
    _REQUEST_DURATION_COUNT.clear()
    _REQUEST_DURATION_MAX.clear()
    _REQUEST_IN_FLIGHT.clear()
    _REQUEST_ERRORS_TOTAL.clear()


def render_prometheus_metrics() -> str:
    lines = [
        "# HELP weitesting_app_info WeiTesting application info.",
        "# TYPE weitesting_app_info gauge",
        'weitesting_app_info{app="ai-test-platform"} 1',
        "# HELP weitesting_process_uptime_seconds Process uptime in seconds.",
        "# TYPE weitesting_process_uptime_seconds gauge",
        f"weitesting_process_uptime_seconds {round(time.time() - _STARTED_AT, 3)}",
        "# HELP weitesting_observability_ready Repo-local observability endpoints are wired.",
        "# TYPE weitesting_observability_ready gauge",
        'weitesting_observability_ready{metrics_endpoint="/metrics",health_endpoint="/health"} 1',
        "# HELP weitesting_http_requests_total HTTP requests grouped by method, route, and status class.",
        "# TYPE weitesting_http_requests_total counter",
    ]
    if not _REQUEST_TOTAL:
        lines.append('weitesting_http_requests_total{method="GET",route="/metrics",status_class="2xx"} 0')
    for (method, route, status_class), count in sorted(_REQUEST_TOTAL.items()):
        lines.append(_metric_line(
            "weitesting_http_requests_total",
            {"method": method, "route": route, "status_class": status_class},
            count,
        ))
    lines.extend([
        "# HELP weitesting_http_request_duration_seconds_sum HTTP request duration sum in seconds.",
        "# TYPE weitesting_http_request_duration_seconds_sum counter",
    ])
    for (method, route), value in sorted(_REQUEST_DURATION_SUM.items()):
        lines.append(_metric_line("weitesting_http_request_duration_seconds_sum", {"method": method, "route": route}, round(value, 6)))
    lines.extend([
        "# HELP weitesting_http_request_duration_seconds_count HTTP request duration count.",
        "# TYPE weitesting_http_request_duration_seconds_count counter",
    ])
    for (method, route), value in sorted(_REQUEST_DURATION_COUNT.items()):
        lines.append(_metric_line("weitesting_http_request_duration_seconds_count", {"method": method, "route": route}, value))
    lines.extend([
        "# HELP weitesting_http_request_errors_total HTTP server errors grouped by method and route.",
        "# TYPE weitesting_http_request_errors_total counter",
    ])
    if not _REQUEST_ERRORS_TOTAL:
        lines.append('weitesting_http_request_errors_total{method="GET",route="/metrics"} 0')
    for (method, route), value in sorted(_REQUEST_ERRORS_TOTAL.items()):
        lines.append(_metric_line("weitesting_http_request_errors_total", {"method": method, "route": route}, value))
    lines.extend([
        "# HELP weitesting_http_request_duration_seconds_max HTTP request duration max in seconds.",
        "# TYPE weitesting_http_request_duration_seconds_max gauge",
    ])
    for (method, route), value in sorted(_REQUEST_DURATION_MAX.items()):
        lines.append(_metric_line("weitesting_http_request_duration_seconds_max", {"method": method, "route": route}, round(value, 6)))
    lines.extend([
        "# HELP weitesting_http_requests_in_flight Current in-flight HTTP requests.",
        "# TYPE weitesting_http_requests_in_flight gauge",
    ])
    if not _REQUEST_IN_FLIGHT:
        lines.append('weitesting_http_requests_in_flight{method="GET",route="/metrics"} 0')
    for (method, route), value in sorted(_REQUEST_IN_FLIGHT.items()):
        lines.append(_metric_line("weitesting_http_requests_in_flight", {"method": method, "route": route}, value))
    return "\n".join(lines) + "\n"
