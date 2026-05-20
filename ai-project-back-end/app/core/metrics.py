from __future__ import annotations

from collections import Counter
import time


_STARTED_AT = time.time()
_REQUEST_TOTAL: Counter[tuple[str, str, str]] = Counter()
_REQUEST_DURATION_SUM: Counter[tuple[str, str]] = Counter()
_REQUEST_DURATION_COUNT: Counter[tuple[str, str]] = Counter()


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    route = path.split("?", 1)[0] or "/"
    status_class = f"{int(status_code / 100)}xx"
    key = (method.upper(), route, status_class)
    duration_key = (method.upper(), route)
    _REQUEST_TOTAL[key] += 1
    _REQUEST_DURATION_SUM[duration_key] += duration_seconds
    _REQUEST_DURATION_COUNT[duration_key] += 1


def _metric_line(name: str, labels: dict[str, str], value: float | int) -> str:
    label_text = ",".join(f'{key}="{val}"' for key, val in labels.items())
    return f"{name}{{{label_text}}} {value}" if label_text else f"{name} {value}"


def render_prometheus_metrics() -> str:
    lines = [
        "# HELP weitesting_app_info WeiTesting application info.",
        "# TYPE weitesting_app_info gauge",
        'weitesting_app_info{app="ai-test-platform"} 1',
        "# HELP weitesting_process_uptime_seconds Process uptime in seconds.",
        "# TYPE weitesting_process_uptime_seconds gauge",
        f"weitesting_process_uptime_seconds {round(time.time() - _STARTED_AT, 3)}",
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
    return "\n".join(lines) + "\n"
