from __future__ import annotations

from app.schemas.doc_ingest import ApiCandidate
from app.services.doc_ingest.k6_agent import generate_k6_script_heuristic


def test_generate_k6_script_heuristic_contains_required_k6_structure() -> None:
    candidates = [
        ApiCandidate(
            id="api_1",
            name="创建用户",
            feature="用户",
            method="POST",
            url="/api/users",
            params={"username": "u", "age": 18},
            headers={"Content-Type": "application/json"},
            expectedStatusCode=201,
            expectedResult='{"code":0}',
            tags=["user"],
            sourceRefs={},
            confidence=0.9,
        ),
        ApiCandidate(
            id="api_2",
            name="获取用户",
            feature="用户",
            method="GET",
            url="/api/users/{userId}",
            params={"userId": 123},
            headers={},
            expectedStatusCode=200,
            expectedResult='{"code":0}',
            tags=["user"],
            sourceRefs={},
            confidence=0.9,
        ),
    ]
    script = generate_k6_script_heuristic(api_candidates=candidates, base_url="http://example.com", vus=5, duration="10s")
    assert "import http from 'k6/http';" in script
    assert "export const options" in script
    assert "export default function" in script
    assert "DEFAULT_BASE_URL" in script
    assert "http://example.com" in script
    assert "pathTemplate" in script
    assert "applyPathParams" in script
