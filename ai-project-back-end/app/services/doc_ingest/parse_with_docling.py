from __future__ import annotations

import hashlib
import re
import time
import uuid
from typing import Any
from urllib.parse import urlparse

from app.schemas.doc_ingest import (
    ApiCandidate,
    DocMeta,
    DocParseResult,
    DocParserInfo,
    DocRaw,
    DocSection,
    DocTable,
    QualityIssue,
    QualityReport,
)


def _now_ts() -> int:
    return int(time.time())


def _sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data or b"")
    return h.hexdigest()


def _detect_source_type(filename: str) -> str:
    name = (filename or "").lower().strip()
    if name.endswith(".pdf"):
        return "PDF"
    if name.endswith(".docx"):
        return "DOCX"
    if name.endswith(".xlsx"):
        return "XLSX"
    if name.endswith(".txt"):
        return "TXT"
    if name.endswith(".md"):
        return "MD"
    return "OTHER"


def _make_issue(code: str, message: str, severity: str = "WARN") -> QualityIssue:
    return QualityIssue(code=code, message=message, severity=severity)


def _evaluate_quality(candidates: list[ApiCandidate]) -> QualityReport:
    total = len(candidates)
    if total == 0:
        return QualityReport(
            hasStructuredApis=False,
            apiCandidateCount=0,
            methodCoverage=0.0,
            urlCoverage=0.0,
            expectedCoverage=0.0,
            issues=[_make_issue("NO_API", "no api candidates", "ERROR")],
        )
    method_ok = sum(1 for c in candidates if c.method and c.method.strip())
    url_ok = sum(1 for c in candidates if c.url and c.url.strip())
    expected_ok = sum(1 for c in candidates if c.expectedResult and c.expectedResult.strip())
    return QualityReport(
        hasStructuredApis=True,
        apiCandidateCount=total,
        methodCoverage=method_ok / total,
        urlCoverage=url_ok / total,
        expectedCoverage=expected_ok / total,
        issues=[],
    )


def _status_from_quality(q: QualityReport) -> str:
    if not q.hasStructuredApis:
        return "FAIL"
    if q.methodCoverage >= 0.6 and q.urlCoverage >= 0.6 and q.apiCandidateCount >= 1:
        return "PASS"
    return "REVIEW"


def _fallback_sections_from_text(text: str) -> list[DocSection]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    blocks = [b.strip() for b in cleaned.split("\n\n") if b and b.strip()]
    items: list[DocSection] = []
    for i, blk in enumerate(blocks[:20], start=1):
        items.append(
            DocSection(
                id=f"s{i}",
                title=None,
                level=None,
                text=blk[:5000],
                page=None,
                tokensEstimate=min(len(blk.split()), 5000),
                confidence=0.3,
            )
        )
    return items


_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}


def _make_candidate_id(seed: str) -> str:
    h = hashlib.sha256()
    h.update(seed.encode("utf-8", errors="ignore"))
    return h.hexdigest()[:24]


def _normalize_url_text(v: str) -> str:
    text = (v or "").strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        try:
            p = urlparse(text)
            if p.path and p.query:
                return f"{p.path}?{p.query}"
            return p.path or text
        except Exception:
            return text
    return text


def _extract_method_url(text: str) -> tuple[str, str] | None:
    t = (text or "").strip().strip("`").strip()
    if not t:
        return None
    parts = t.split()
    if len(parts) < 2:
        return None
    m = parts[0].strip().upper()
    if m not in _HTTP_METHODS:
        return None
    u = _normalize_url_text(" ".join(parts[1:]).strip())
    if not u:
        return None
    return m, u


def _parse_markdown_api_candidates(text: str, *, default_feature: str) -> list[ApiCandidate]:
    lines = (text or "").splitlines()
    if not lines:
        return []

    candidates: list[ApiCandidate] = []
    seen: set[tuple[str, str]] = set()

    current_feature = (default_feature or "DEFAULT").strip()[:128] or "DEFAULT"
    current_title: str | None = None

    last_response_label_line: int | None = None
    in_code = False
    code_lang = ""
    code_start_line = 0
    code_buf: list[str] = []
    last_candidate_line: int | None = None

    request_url_label = re.compile(r"请求\s*URL|Request\s*URL", re.IGNORECASE)
    response_label = re.compile(r"^\s*\*\*\s*(响应|Response)\s*[:：]\s*\*\*\s*$", re.IGNORECASE)
    inline_method_url = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\b\s+([/][^\s`]+)", re.IGNORECASE)

    def _push_candidate(method: str, url: str, *, source: str, line_no: int) -> None:
        nonlocal last_candidate_line
        m = (method or "").strip().upper()
        u = _normalize_url_text(url)
        if not m or not u:
            return
        k = (m, u)
        if k in seen:
            return
        seen.add(k)

        title = (current_title or "").strip()[:100] if current_title else ""
        name = title if title else f"{m} {u}"[:100]
        cid = _make_candidate_id(f"{default_feature}|{name}|{m}|{u}|{line_no}|{source}")
        candidates.append(
            ApiCandidate(
                id=cid,
                name=name,
                feature=current_feature,
                method=m,
                url=u,
                params={},
                headers={},
                expectedStatusCode=None,
                expectedResult=None,
                tags=[],
                sourceRefs={"line": line_no, "source": source},
                confidence=0.75 if source == "request_url" else 0.6,
            )
        )
        last_candidate_line = line_no

    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        s = line.strip()
        if not s:
            continue

        if s.startswith("```"):
            if not in_code:
                in_code = True
                code_lang = s[3:].strip().lower()
                code_start_line = idx
                code_buf = []
                continue
            in_code = False
            block = "\n".join(code_buf).strip()
            if block and last_response_label_line is not None and (code_start_line - last_response_label_line) <= 3:
                if candidates and last_candidate_line is not None and (code_start_line - last_candidate_line) <= 30:
                    c = candidates[-1]
                    if not (c.expectedResult or "").strip():
                        c.expectedResult = block[:5000]
            code_lang = ""
            code_start_line = 0
            code_buf = []
            continue

        if in_code:
            code_buf.append(line)
            continue

        hm = re.match(r"^(#{1,6})\s+(.*)$", s)
        if hm:
            level = len(hm.group(1))
            title = hm.group(2).strip()
            if level <= 2 and title:
                current_feature = title[:128]
            if level <= 4 and title:
                current_title = title[:100]
            continue

        if response_label.match(s):
            last_response_label_line = idx
            continue

        if request_url_label.search(s):
            chunks = re.findall(r"`([^`]+)`", s)
            token = chunks[0] if chunks else s.split(":", 1)[-1].split("：", 1)[-1].strip()
            mu = _extract_method_url(token)
            if mu:
                _push_candidate(mu[0], mu[1], source="request_url", line_no=idx)
                continue

        mm = inline_method_url.search(s)
        if mm:
            _push_candidate(mm.group(1), mm.group(2), source="inline_method_url", line_no=idx)
            continue

    return candidates


def _parse_with_docling(file_bytes: bytes, filename: str) -> tuple[list[DocSection], list[ApiCandidate], list[DocTable], list[QualityIssue]]:
    try:
        import docling  # type: ignore
    except Exception:
        return [], [], [], [_make_issue("DOCLING_NOT_AVAILABLE", "docling not installed", "ERROR")]
    return [], [], [], [_make_issue("DOCLING_NOT_WIRED", "docling pipeline not integrated", "WARN")]


def parse_document(file_bytes: bytes, filename: str, *, job_id: str | None = None) -> DocParseResult:
    source_type = _detect_source_type(filename)
    file_hash = _sha256(file_bytes)
    sections: list[DocSection] = []
    candidates: list[ApiCandidate] = []
    tables: list[DocTable] = []
    issues: list[QualityIssue] = []

    s2, c2, t2, i2 = _parse_with_docling(file_bytes, filename)
    sections.extend(s2)
    candidates.extend(c2)
    tables.extend(t2)
    issues.extend(i2)

    if not sections:
        text_guess = ""
        try:
            text_guess = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text_guess = ""
        sec_fb = _fallback_sections_from_text(text_guess)
        if sec_fb:
            sections = sec_fb
        else:
            issues.append(_make_issue("NO_TEXT", "no text extracted", "ERROR"))
    else:
        try:
            text_guess = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text_guess = ""

    if not candidates and text_guess.strip():
        fb_feature = (filename or "").strip()
        c_fb = _parse_markdown_api_candidates(text_guess, default_feature=fb_feature or "DEFAULT")
        if c_fb:
            candidates.extend(c_fb)
            issues.append(_make_issue("FALLBACK_MD_USED", "fallback markdown parser applied", "INFO"))

    q = _evaluate_quality(candidates)
    if issues:
        q.issues.extend(issues)
    status = _status_from_quality(q)
    if status == "FAIL":
        pass

    meta = DocMeta(
        jobId=job_id,
        sourceType=source_type,
        fileName=filename or "unknown",
        fileHash=file_hash,
        parsedAt=_now_ts(),
        parser=DocParserInfo(name="docling", version="unknown"),
        language=None,
        pageCount=None,
    )
    raw = DocRaw(textDigest=" ".join([s.text[:200] for s in sections])[:2000], attachments=[])
    return DocParseResult(meta=meta, sections=sections, apiCandidates=candidates, tables=tables, quality=q, raw=raw, status=status)
