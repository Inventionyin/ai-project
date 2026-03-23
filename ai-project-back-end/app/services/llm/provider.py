from __future__ import annotations

import os
from typing import Iterable

from app.schemas.doc_ingest import ApiCandidate


class LlmProvider:
    def enhance(self, items: Iterable[ApiCandidate]) -> list[ApiCandidate]:
        return list(items)


def get_provider() -> LlmProvider:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    return LlmProvider()

