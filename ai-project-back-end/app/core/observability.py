"""Observability utilities: sensitive-data masking and distributed tracing."""
from __future__ import annotations

import re
import time
import uuid
from collections.abc import Mapping
from contextvars import ContextVar
from typing import Any

_SENSITIVE_KEY_PATTERN = re.compile(r"(password|token|secret|apikey|api_key|authorization|cookie|bearer)", re.IGNORECASE)
_BEARER_PATTERN = re.compile(r"(bearer\s+)[A-Za-z0-9._\-+=/]+", re.IGNORECASE)


def mask_sensitive_text(value: str) -> str:
    text = str(value or "")
    text = _BEARER_PATTERN.sub(r"\1******", text)
    return text


def _mask_scalar(key: str, value: Any) -> Any:
    if _SENSITIVE_KEY_PATTERN.search(key):
        return "******"
    if isinstance(value, str):
        return mask_sensitive_text(value)
    return value


def mask_sensitive_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in data.items():
        key_text = str(key)
        if isinstance(value, Mapping):
            masked[key_text] = mask_sensitive_mapping(value)
            continue
        if isinstance(value, list):
            masked[key_text] = [
                mask_sensitive_mapping(item) if isinstance(item, Mapping) else _mask_scalar(key_text, item)
                for item in value
            ]
            continue
        masked[key_text] = _mask_scalar(key_text, value)
    return masked


# ---------------------------------------------------------------------------
# Distributed tracing context
# ---------------------------------------------------------------------------

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_id: ContextVar[str] = ContextVar("span_id", default="")
_request_start: ContextVar[float] = ContextVar("request_start", default=0.0)


def get_trace_id() -> str:
    """Return the current trace-id (or empty string if none)."""
    return _trace_id.get()


def get_span_id() -> str:
    """Return the current span-id (or empty string if none)."""
    return _span_id.get()


def get_request_duration_ms() -> float:
    """Return elapsed milliseconds since ``init_trace`` was called."""
    start = _request_start.get()
    if start <= 0:
        return 0.0
    return (time.time() - start) * 1000


def init_trace(request_id: str | None = None) -> dict[str, str]:
    """Initialize a new trace context for the current request.

    Returns a dict with ``traceId`` and ``spanId`` that can be injected
    into response headers or log records.
    """
    tid = request_id or uuid.uuid4().hex
    sid = uuid.uuid4().hex[:16]
    _trace_id.set(tid)
    _span_id.set(sid)
    _request_start.set(time.time())
    return {"traceId": tid, "spanId": sid}
