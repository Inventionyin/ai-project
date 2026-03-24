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

    def chat(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> dict:
        return {}

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


def _normalize_usage(raw: object) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    prompt_tokens = raw.get("prompt_tokens", raw.get("promptTokens"))
    completion_tokens = raw.get("completion_tokens", raw.get("completionTokens"))
    total_tokens = raw.get("total_tokens", raw.get("totalTokens"))
    if prompt_tokens is None and completion_tokens is None and total_tokens is None:
        return None
    out: dict[str, int] = {}
    if prompt_tokens is not None:
        out["promptTokens"] = int(prompt_tokens)
    if completion_tokens is not None:
        out["completionTokens"] = int(completion_tokens)
    if total_tokens is not None:
        out["totalTokens"] = int(total_tokens)
    return out or None


# 配置大模型? 还没有配置,脚本编写的效果不好
class OpenAICompatibleProvider(LlmProvider):
    def __init__(self) -> None:
        self._api_key = (os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or "").strip()
        self._base_url = (os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").strip()
        self._base_url = self._base_url or "https://api.deepseek.com"
        self._model = (os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip() or "deepseek-chat"
        self._timeout_s = float(os.getenv("LLM_TIMEOUT_SECONDS", "").strip() or "60")

    def _post_chat_completions(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> dict:
        url = f"{self._base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        body: dict = {
            "model": self._model,
            "temperature": float(temperature),
            "messages": messages,
            "stream": False,
        }
        if max_tokens is not None:
            body["max_tokens"] = int(max_tokens)
        resp = requests.post(url, headers=headers, json=body, timeout=self._timeout_s)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("LLM response is not a JSON object")
        return data

    def chat(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> dict:
        if not self._api_key:
            return {}
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": str(system)})
        messages.append({"role": "user", "content": str(prompt)})
        data = self._post_chat_completions(messages=messages, temperature=temperature, max_tokens=max_tokens)
        content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content"))  # type: ignore[union-attr]
        return {
            "baseUrl": self._base_url,
            "model": data.get("model") or self._model,
            "responseId": data.get("id"),
            "content": str(content or ""),
            "usage": _normalize_usage(data.get("usage")),
        }

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

        data = self._post_chat_completions(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=None,
        )
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
    if provider in {"openai", "openai_compatible", "deepseek"}:
        return OpenAICompatibleProvider()
    if provider:
        return LlmProvider()
    if (os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or "").strip():
        return OpenAICompatibleProvider()
    return LlmProvider()
