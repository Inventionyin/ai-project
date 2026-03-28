from __future__ import annotations

from app.schemas.doc_ingest import ApiCandidate
from app.services.doc_ingest.case_generator import _heuristic_rows


def test_register_heuristic_rows_match_expected_fields() -> None:
    candidate = ApiCandidate(
        id="api_register",
        name="注册",
        feature="认证模块",
        method="POST",
        url="/api/auth/register",
        params={},
        headers={},
        expectedStatusCode=200,
        expectedResult="",
        tags=["auth"],
        sourceRefs={},
        confidence=0.9,
    )
    rows = _heuristic_rows([candidate])
    assert len(rows) == 18

    ok = rows[0]
    assert ok.test_type == "positive"
    assert ok.expected_status_code == 200
    assert ok.apiHeaders.get("Content-Type") == "application/json"
    assert ok.apiParams.get("phone") == "${env.registerPhone}"
    assert ok.apiParams.get("username") == "${env.registerUsername}"
    assert ok.apiParams.get("password") == "${env.registerPassword}"
    assert ok.apiParams.get("confirmPassword") == "${env.registerPassword}"
    assert '"code":0' in str(ok.expectedResult or "")
    pre = ok.preconditions
    assert isinstance(pre, dict)
    assert "env.registerPhone" in (pre.get("requires") or [])
    assert "env.registerUsername" in (pre.get("requires") or [])
    assert "env.registerPassword" in (pre.get("requires") or [])

    post = ok.postconditions
    assert isinstance(post, dict)
    exports = post.get("exports") or {}
    assert "registerUserId" in exports
    assert "registerPhone" in exports
    assert "registerUsername" in exports

    missing_phone = rows[1]
    assert missing_phone.test_type == "negative"
    assert '"code":40001' in str(missing_phone.expectedResult or "")

    conflict_phone = rows[16]
    assert '"code":40901' in str(conflict_phone.expectedResult or "")
    pre2 = conflict_phone.preconditions
    assert isinstance(pre2, dict)
    assert "env.existingPhone" in (pre2.get("requires") or [])

