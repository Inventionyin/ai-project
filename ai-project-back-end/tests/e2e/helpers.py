from __future__ import annotations


def assert_success(body: dict) -> dict:
    assert body["code"] == 0, body
    assert body.get("data") is not None
    return body["data"]


def unique_phone(prefix: str = "139") -> str:
    import uuid

    return f"{prefix}{uuid.uuid4().int % 100_000_000:08d}"
