from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Iterable

from app.schemas.doc_ingest import ApiCandidate, DocParseResult


_DEFAULT_PRECONDITIONS_OBJ: dict = {
    "dependsOn": [],
    "requires": [],
    "bind": {},
}

_DEFAULT_POSTCONDITIONS_OBJ: dict = {
    "asserts": [],
    "exports": {},
}


def _normalize_method(v: str | None) -> str:
    if not v:
        return "GET"
    return str(v).strip().upper()


def _normalize_url(v: str | None) -> str:
    if not v or not str(v).strip():
        return "/unknown"
    return str(v).strip()


def _normalize_feature(v: str | None) -> str:
    if not v or not str(v).strip():
        return "DEFAULT"
    return str(v).strip()[:128]


def _normalize_title(c: ApiCandidate) -> str:
    if c.name and c.name.strip():
        return c.name.strip()[:100]
    m = _normalize_method(c.method)
    u = _normalize_url(c.url)
    return f"{m} {u}"[:100]


def _normalize_expected_result(v: str | None) -> str:
    text = (v or "").strip()
    return text if text else "{}"


def _json_obj_text(obj: dict | None) -> str:
    return json.dumps(obj or {}, ensure_ascii=False)


def _tags_text(tags: list[str] | None) -> str:
    tags = tags or []
    return ",".join([t for t in tags if t.strip()][:50])


def _row_from_candidate(c: ApiCandidate) -> dict[str, str]:
    expected_status_code = c.expectedStatusCode if c.expectedStatusCode is not None else 200
    expected_result = (c.expectedResult or "").strip()
    if not expected_result:
        if 200 <= expected_status_code <= 299:
            expected_result = '"code":0'
        else:
            expected_result = "{}"
    row: dict[str, str] = {
        "test_case_id": "",
        "feature": _normalize_feature(c.feature),
        "title": _normalize_title(c),
        "apiMethod": _normalize_method(c.method),
        "apiUrl": _normalize_url(c.url),
        "apiHeaders": _json_obj_text(c.headers),
        "apiParams": _json_obj_text(c.params),
        "expected_status_code": str(expected_status_code),
        "expectedResult": expected_result,
        "test_type": "positive",
        "priority": "P0",
        "status": "DRAFT",
        "type": "API",
        "preconditions": _json_obj_text(_DEFAULT_PRECONDITIONS_OBJ),
        "postconditions": _json_obj_text(_DEFAULT_POSTCONDITIONS_OBJ),
        "tags": _tags_text(c.tags),
    }
    return row


def build_csv_from_doc_parse(result: DocParseResult) -> tuple[str, str, int]:
    items: Iterable[ApiCandidate] = result.apiCandidates or []
    rows = [_row_from_candidate(c) for c in items]
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    fname = f"api_test_cases_{ts}.csv"
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "test_case_id",
            "feature",
            "title",
            "apiMethod",
            "apiUrl",
            "apiHeaders",
            "apiParams",
            "expected_status_code",
            "expectedResult",
            "test_type",
            "priority",
            "status",
            "type",
            "preconditions",
            "postconditions",
            "tags",
        ],
    )
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    csv_text = buf.getvalue()
    return fname, csv_text, len(rows)
