from __future__ import annotations

import uuid
from pathlib import Path

from app.services.testcase_import import _build_row_payloads, _parse_csv_rows


def test_build_row_payloads_from_sample_csv() -> None:
    root = Path(__file__).resolve().parents[2]
    sample = root / "test_cases" / "api_test_cases_20260322120000.csv"
    content = sample.read_bytes()
    rows = _parse_csv_rows(content)
    project_id = str(uuid.uuid4())
    payloads, errors = _build_row_payloads(project_id=project_id, rows=rows[:5], mode="partial")
    assert errors == []
    assert len(payloads) == 5
    assert payloads[0].payload.projectId == project_id
    assert payloads[0].payload.type == "API"


def test_build_row_payloads_rejects_invalid_json() -> None:
    project_id = str(uuid.uuid4())
    rows = [
        {
            "test_case_id": "TC001",
            "feature": "认证",
            "title": "login",
            "apimethod": "POST",
            "apiurl": "/api/auth/login",
            "apiheaders": "{bad}",
            "apiparams": "{}",
            "expected_status_code": "200",
            "expectedresult": '{"code":0}',
            "priority": "P0",
            "status": "DRAFT",
            "type": "API",
            "preconditions": "{}",
            "postconditions": "{}",
            "tags": "auth,login",
        }
    ]
    payloads, errors = _build_row_payloads(project_id=project_id, rows=rows, mode="partial")
    assert payloads == []
    assert len(errors) == 1
    assert errors[0].field == "apiHeaders"

