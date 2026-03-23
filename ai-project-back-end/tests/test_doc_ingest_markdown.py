from __future__ import annotations

import json
from pathlib import Path

from app.schemas.doc_ingest import ApiCandidate
from app.schemas.testcase_gen import GeneratedTestCaseRow
from app.services.doc_ingest.case_generator import _heuristic_rows, rows_to_csv_dicts
from app.services.doc_ingest.csv_builder import build_csv_from_doc_parse
from app.services.doc_ingest.parse_with_docling import parse_document
from app.services.testcase_import import _parse_csv_rows


def test_markdown_doc_ingest_generates_non_empty_csv_rows() -> None:
    root = Path(__file__).resolve().parents[2]
    doc = root / "docs" / "API.md"
    content = doc.read_bytes()
    result = parse_document(content, doc.name, job_id=None)
    assert len(result.apiCandidates) > 0

    _, csv_text, count = build_csv_from_doc_parse(result)
    assert count > 0
    rows = _parse_csv_rows(csv_text.encode("utf-8"))
    assert len(rows) == count


def test_heuristic_rows_generate_positive_negative_boundary() -> None:
    candidate = ApiCandidate(
        id="api_1",
        name="用户登录",
        feature="认证",
        method="post",
        url="/api/auth/login",
        params={"username": "user", "password": "pass"},
        headers={"Content-Type": "application/json"},
        expectedStatusCode=200,
        expectedResult='{"code":0}',
        tags=["auth", "login"],
        sourceRefs={},
        confidence=0.95,
    )
    rows = _heuristic_rows([candidate])
    assert len(rows) == 3
    assert [r.test_case_id for r in rows] == ["TC001001", "TC001002", "TC001003"]
    assert [r.test_type for r in rows] == ["positive", "negative", "boundary"]
    assert rows[0].expected_status_code == 200
    assert rows[1].expected_status_code == 200
    assert rows[2].expected_status_code == 200
    assert '"code":40001' in str(rows[1].expectedResult or "")
    assert '"code":40001' in str(rows[2].expectedResult or "")
    assert rows[1].apiParams != rows[0].apiParams
    assert rows[2].apiParams != rows[0].apiParams
    assert isinstance(rows[0].postconditions, dict)
    assert "exports" in rows[0].postconditions


def test_rows_to_csv_dicts_coerce_json_text_columns() -> None:
    row = GeneratedTestCaseRow(
        test_case_id="TC001001",
        feature="认证",
        title="用户登录_正常流程",
        apiMethod="POST",
        apiUrl="/api/auth/login",
        apiHeaders='{"Authorization":"Bearer token"}',
        apiParams='{"username":"tester"}',
        expected_status_code="201",
        expectedResult='{"code":0}',
        test_type="positive",
        priority="P0",
        status="DRAFT",
        type="API",
        preconditions='{"dependsOn":[],"bind":{}}',
        postconditions='{"asserts":[],"exports":{}}',
        tags="auth,positive",
    )
    csv_rows = rows_to_csv_dicts([row])
    assert len(csv_rows) == 1
    got = csv_rows[0]
    assert got["expected_status_code"] == "201"
    assert json.loads(got["apiHeaders"]) == {"Authorization": "Bearer token"}
    assert json.loads(got["apiParams"]) == {"username": "tester"}
    assert json.loads(got["preconditions"]) == {"dependsOn": [], "bind": {}}
    assert json.loads(got["postconditions"]) == {"asserts": [], "exports": {}}


def test_parameterize_url_and_params_add_requires() -> None:
    candidate = ApiCandidate(
        id="api_2",
        name="获取用户",
        feature="用户",
        method="GET",
        url="/api/users/{userId}",
        params={"userId": 123, "name": "n"},
        headers={},
        expectedStatusCode=200,
        expectedResult='{"code":0}',
        tags=["user"],
        sourceRefs={},
        confidence=0.9,
    )
    rows = _heuristic_rows([candidate])
    assert rows[0].apiUrl == "/api/users/${userId}"
    assert rows[0].apiParams.get("userId") == "${userId}"
    pre = rows[0].preconditions
    assert isinstance(pre, dict)
    assert "requires" in pre
    assert "userId" in (pre.get("requires") or [])
