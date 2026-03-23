from __future__ import annotations

from app.schemas.doc_ingest import ApiCandidate, DocParseResult, QualityIssue
from app.services.llm.provider import get_provider


def apply_llm_enhancement(result: DocParseResult, mode: str) -> DocParseResult:
    m = (mode or "OFF").strip().upper()
    if m == "OFF":
        return result
    provider = get_provider()
    try:
        items = provider.enhance(result.apiCandidates)
    except Exception as e:
        q = result.quality
        q.issues.append(QualityIssue(code="LLM_ERROR", message=str(e), severity="ERROR"))
        return result
    if m == "SUGGEST":
        q = result.quality
        q.issues.append(QualityIssue(code="LLM_SUGGEST", message="suggestions available", severity="INFO"))
        return result
    if m == "AUTO":
        if isinstance(items, list) and items:
            result.apiCandidates = items
            q = result.quality
            q.issues.append(QualityIssue(code="LLM_APPLIED", message="auto enhancement applied", severity="INFO"))
            return result
        q = result.quality
        q.issues.append(QualityIssue(code="LLM_NO_CHANGE", message="no effective enhancement", severity="WARN"))
        return result
    q = result.quality
    q.issues.append(QualityIssue(code="LLM_MODE_INVALID", message=m, severity="WARN"))
    return result

