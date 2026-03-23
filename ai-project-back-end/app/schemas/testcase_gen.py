from __future__ import annotations

import json
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema


class GeneratedTestCaseRow(BaseSchema):
    test_case_id: str = Field(default="")
    feature: str = Field(default="DEFAULT", max_length=128)
    title: str = Field(min_length=1, max_length=100)
    apiMethod: str = Field(default="GET", max_length=16)
    apiUrl: str = Field(default="/unknown", max_length=1024)
    apiHeaders: dict[str, Any] | str = Field(default_factory=dict)
    apiParams: dict[str, Any] | str = Field(default_factory=dict)
    expected_status_code: int | str = Field(default=200)
    expectedResult: str = Field(default="{}")
    test_type: str = Field(default="positive", max_length=32)
    priority: str = Field(default="P1", max_length=16)
    status: str = Field(default="DRAFT", max_length=32)
    type: str = Field(default="API", max_length=16)
    preconditions: dict[str, Any] | str = Field(default_factory=dict)
    postconditions: dict[str, Any] | str = Field(default_factory=dict)
    tags: list[str] | str = Field(default="")

    @field_validator("apiMethod", mode="before")
    @classmethod
    def _normalize_method(cls, v: object) -> str:
        text = str(v or "").strip().upper()
        return text or "GET"

    @field_validator("apiUrl", mode="before")
    @classmethod
    def _normalize_url(cls, v: object) -> str:
        text = str(v or "").strip()
        return text or "/unknown"

    @field_validator("expected_status_code", mode="before")
    @classmethod
    def _normalize_status_code(cls, v: object) -> int:
        if v is None:
            return 200
        if isinstance(v, int):
            return v
        text = str(v).strip()
        if not text:
            return 200
        return int(text)

    @field_validator("apiHeaders", "apiParams", "preconditions", "postconditions", mode="before")
    @classmethod
    def _coerce_json_obj(cls, v: object) -> dict[str, Any] | str:
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            text = v.strip()
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except Exception:
                return v
            if isinstance(parsed, dict):
                return parsed
            return v
        return str(v)

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, v: object) -> list[str] | str:
        if v is None:
            return ""
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()][:50]
        return str(v)

