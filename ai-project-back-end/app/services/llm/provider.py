from __future__ import annotations

import json
import os
import re
from typing import Iterable

import requests

from app.schemas.doc_ingest import ApiCandidate
from app.schemas.testcase_gen import GeneratedTestCaseRow
from app.services.llm.skills.api_doc_test_generator import build_system_prompt


class LlmProvider:
    def enhance(self, items: Iterable[ApiCandidate]) -> list[ApiCandidate]:
        return list(items)

    def generate_testcases(
        self,
        *,
        skill_id: str,
        instruction: str,
        api_candidates: list[ApiCandidate],
        doc_text: str,
        max_cases: int,
    ) -> list[GeneratedTestCaseRow]:
        return []


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if not t.startswith("```"):
        return t
    t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _extract_json_array(text: str) -> list:
    t = _strip_code_fences(text)
    start = t.find("[")
    end = t.rfind("]")
    if start >= 0 and end > start:
        t = t[start : end + 1]
    parsed = json.loads(t)
    if not isinstance(parsed, list):
        raise ValueError("LLM output is not a JSON array")
    return parsed


class OpenAICompatibleProvider(LlmProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("LLM_API_KEY", "").strip()
        self._base_url = os.getenv("LLM_BASE_URL", "").strip() or "https://api.openai.com/v1"
        self._model = os.getenv("LLM_MODEL", "").strip() or "gpt-4o-mini"
        self._timeout_s = float(os.getenv("LLM_TIMEOUT_SECONDS", "").strip() or "60")

    def generate_testcases(
        self,
        *,
        skill_id: str,
        instruction: str,
        api_candidates: list[ApiCandidate],
        doc_text: str,
        max_cases: int,
    ) -> list[GeneratedTestCaseRow]:
        if not self._api_key:
            return []

        system_prompt = build_system_prompt()
        candidates_payload: list[dict] = []
        for c in api_candidates[:200]:
            candidates_payload.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "feature": c.feature,
                    "method": c.method,
                    "url": c.url,
                    "params": c.params,
                    "headers": c.headers,
                    "expectedStatusCode": c.expectedStatusCode,
                    "expectedResult": c.expectedResult,
                    "tags": c.tags,
                    "confidence": c.confidence,
                }
            )

        user_payload = {
            "skillId": skill_id,
            "instruction": instruction,
            "maxCases": int(max_cases),
            "apiCandidates": candidates_payload,
            "docText": (doc_text or "")[:12000],
        }

        url = f"{self._base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        body = {
            "model": self._model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }
        resp = requests.post(url, headers=headers, json=body, timeout=self._timeout_s)
        resp.raise_for_status()
        data = resp.json()
        content = (
            (((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content")  # type: ignore[union-attr]
        )
        rows_raw = _extract_json_array(str(content or ""))
        rows: list[GeneratedTestCaseRow] = []
        for item in rows_raw[: max(1, int(max_cases))]:
            rows.append(GeneratedTestCaseRow.model_validate(item))
        return rows


def get_provider() -> LlmProvider:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider in {"openai", "openai_compatible"}:
        return OpenAICompatibleProvider()
    return LlmProvider()
