from __future__ import annotations

import json
from typing import Iterable
import re

from fastapi import APIRouter, Depends, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.doc_ingest import DocCsvGenerateData, DocParseResult, QualityIssue
from app.services.doc_ingest.parse_with_docling import parse_document
from app.services.doc_ingest.csv_builder import build_csv_from_doc_parse, build_csv_from_rows
from app.schemas.testcase_import import TestCaseImportData
from app.services.testcase_import import import_testcases_from_file
from app.services.doc_ingest.llm_enhancer import apply_llm_enhancement
from app.services.doc_ingest.case_generator import generate_testcase_rows, rows_to_csv_dicts

router = APIRouter(prefix="/doc-ingest")

def _parse_candidate_ids(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return []

    parsed: object
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = [item for item in text.split(",")]

    if not isinstance(parsed, list):
        return []

    items: list[str] = []
    seen: set[str] = set()
    for item in parsed:
        v = str(item).strip()
        if not v or v in seen:
            continue
        seen.add(v)
        items.append(v)
        if len(items) >= 2000:
            break
    return items

def _filter_candidates(items: Iterable, candidate_ids: list[str] | None) -> list:
    if candidate_ids is None:
        return list(items)
    if not candidate_ids:
        return []
    allowed = set(candidate_ids)
    return [c for c in items if getattr(c, "id", None) in allowed]

def _extract_instruction_keywords(instruction: str | None) -> list[str]:
    raw = str(instruction or "").strip()
    if not raw:
        return []
    keywords: list[str] = []
    module_matches = re.findall(r"(?:模块|module)\s*[：:]\s*([^\n;；]+)", raw, flags=re.IGNORECASE)
    for m in module_matches:
        keywords.extend(re.split(r"[,，、|/ ]+", m))
    if not keywords:
        quoted = re.findall(r"[“\"'‘]([^”\"'’]{1,32})[”\"'’]", raw)
        if quoted and re.search(r"(只生成|仅生成|只要|模块|module)", raw):
            keywords.extend(quoted)
    cleaned: list[str] = []
    seen: set[str] = set()
    for k in keywords:
        k2 = str(k or "").strip()
        if not k2:
            continue
        key = k2.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(k2[:32])
    return cleaned

def _filter_candidates_by_instruction(items: Iterable, instruction: str | None) -> list:
    keywords = _extract_instruction_keywords(instruction)
    if not keywords:
        return list(items)
    lowered = [k.lower() for k in keywords]
    out: list = []
    for c in items:
        feature = getattr(c, "feature", None) or ""
        name = getattr(c, "name", None) or ""
        url = getattr(c, "url", None) or ""
        tags = getattr(c, "tags", None) or []
        hay = " ".join([str(feature), str(name), str(url), " ".join([str(t) for t in tags])]).lower()
        if any(k in hay for k in lowered):
            out.append(c)
    return out

@router.post("/preview", response_model=ApiResponse[DocParseResult])
async def preview(
    llmMode: str = Form(default="OFF"),
    instruction: str = Form(default=""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DocParseResult]:
    content = await file.read()
    try:
        result = parse_document(content, file.filename or "unknown", job_id=None)
        result = apply_llm_enhancement(result, llmMode)
        before = len(result.apiCandidates or [])
        result.apiCandidates = _filter_candidates_by_instruction(result.apiCandidates or [], instruction)
        after = len(result.apiCandidates or [])
        if before != after:
            result.quality.issues.append(QualityIssue(code="INSTRUCTION_FILTER", message=f"{after}/{before}", severity="INFO"))
    finally:
        await file.close()
    return ApiResponse(data=result, requestId=request_id)

@router.post("/generate-csv", response_model=ApiResponse[DocCsvGenerateData])
async def generate_csv(
    llmMode: str = Form(default="OFF"),
    caseGenMode: str = Form(default="OFF"),
    skillId: str = Form(default="api-doc-test-generator"),
    maxCases: int = Form(default=200),
    candidateIds: str | None = Form(default=None),
    instruction: str = Form(default=""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DocCsvGenerateData]:
    content = await file.read()
    try:
        result = parse_document(content, file.filename or "unknown", job_id=None)
        result = apply_llm_enhancement(result, llmMode)
        selected_ids = _parse_candidate_ids(candidateIds)
        before = len(result.apiCandidates or [])
        result.apiCandidates = _filter_candidates(result.apiCandidates or [], selected_ids)
        result.apiCandidates = _filter_candidates_by_instruction(result.apiCandidates or [], instruction)
        after = len(result.apiCandidates or [])
        if before != after:
            result.quality.issues.append(QualityIssue(code="INSTRUCTION_FILTER", message=f"{after}/{before}", severity="INFO"))
        rows = generate_testcase_rows(
            result=result,
            instruction=instruction,
            skill_id=str(skillId or "api-doc-test-generator").strip() or "api-doc-test-generator",
            max_cases=max(1, min(2000, int(maxCases or 200))),
            mode=caseGenMode,
        )
        if rows:
            fname, csv_text, count = build_csv_from_rows(rows_to_csv_dicts(rows), fname_prefix="api_test_cases")
        else:
            fname, csv_text, count = build_csv_from_doc_parse(result)
        data = DocCsvGenerateData(fileName=fname, csvText=csv_text, itemCount=count, status=result.status)
    finally:
        await file.close()
    return ApiResponse(data=data, requestId=request_id)

@router.post("/generate-import", response_model=ApiResponse[TestCaseImportData])
async def generate_and_import(
    projectId: str = Form(...),
    mode: str = Form(default="partial"),
    llmMode: str = Form(default="OFF"),
    caseGenMode: str = Form(default="OFF"),
    skillId: str = Form(default="api-doc-test-generator"),
    maxCases: int = Form(default=200),
    candidateIds: str | None = Form(default=None),
    instruction: str = Form(default=""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[TestCaseImportData]:
    pid = uuid.UUID(projectId)
    content = await file.read()
    try:
        result = parse_document(content, file.filename or "unknown", job_id=None)
        result = apply_llm_enhancement(result, llmMode)
        selected_ids = _parse_candidate_ids(candidateIds)
        before = len(result.apiCandidates or [])
        result.apiCandidates = _filter_candidates(result.apiCandidates or [], selected_ids)
        result.apiCandidates = _filter_candidates_by_instruction(result.apiCandidates or [], instruction)
        after = len(result.apiCandidates or [])
        if before != after:
            result.quality.issues.append(QualityIssue(code="INSTRUCTION_FILTER", message=f"{after}/{before}", severity="INFO"))
        rows = generate_testcase_rows(
            result=result,
            instruction=instruction,
            skill_id=str(skillId or "api-doc-test-generator").strip() or "api-doc-test-generator",
            max_cases=max(1, min(2000, int(maxCases or 200))),
            mode=caseGenMode,
        )
        if rows:
            fname, csv_text, count = build_csv_from_rows(rows_to_csv_dicts(rows), fname_prefix="api_test_cases")
        else:
            fname, csv_text, count = build_csv_from_doc_parse(result)
        data = await import_testcases_from_file(
            db,
            user=user,
            project_id=pid,
            filename=fname,
            file_bytes=csv_text.encode("utf-8"),
            mode=mode,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await file.close()
    return ApiResponse(data=data, requestId=request_id)
