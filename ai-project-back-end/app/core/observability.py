from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from typing import Any

_SENSITIVE_KEY_PATTERN = re.compile(r"(password|token|secret|apikey|api_key|authorization|cookie|bearer)", re.IGNORECASE)
_BEARER_PATTERN = re.compile(r"(bearer\s+)[A-Za-z0-9._\-+=/]+", re.IGNORECASE)
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"


def normalize_request_id(value: str | None) -> str:
    raw_request_id = str(value or "").strip()
    if not raw_request_id:
        return generate_request_id()
    request_id = re.sub(r"[^A-Za-z0-9_.:-]", "-", raw_request_id)[:64].strip("-")
    if request_id and _REQUEST_ID_PATTERN.fullmatch(request_id):
        return request_id
    return generate_request_id()


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
