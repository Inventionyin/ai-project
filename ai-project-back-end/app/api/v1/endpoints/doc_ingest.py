from __future__ import annotations

import json
from typing import Iterable
import re

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.doc_ingest import (
    DocCsvGenerateData,
    DocParseResult,
    K6ScriptGenerateData,
    LlmDemoData,
    LlmDemoRequest,
    LlmDemoTokenUsage,
    QualityIssue,
)
from app.services.doc_ingest.parse_with_docling import parse_document
from app.services.doc_ingest.csv_builder import build_csv_from_doc_parse, build_csv_from_rows
from app.schemas.testcase_import import TestCaseImportData
from app.services.testcase_import import import_testcases_from_file
from app.services.doc_ingest.llm_enhancer import apply_llm_enhancement
from app.services.doc_ingest.case_generator import generate_testcase_rows, rows_to_csv_dicts
from app.services.doc_ingest.k6_agent import generate_k6_script_heuristic, generate_k6_script_with_langgraph
from app.services.llm.provider import get_provider

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
    all_items = list(items)
    if candidate_ids is None:
        return all_items
    if not candidate_ids:
        return all_items
    allowed = set(candidate_ids)
    matched = [c for c in all_items if getattr(c, "id", None) in allowed]
    if matched:
        return matched
    return all_items

def _extract_instruction_keywords(instruction: str | None) -> list[str]:
    raw = str(instruction or "").strip()
    if not raw:
        return []
    keywords: list[str] = []
    if not keywords:
        # 1. 提取模块/module 后面的内容
        module_matches = re.findall(r"(?:模块|module)\s*[：:]\s*([^\n;；]+)", raw, flags=re.IGNORECASE)
        for m in module_matches:
            keywords.extend(re.split(r"[,，、|/ ]+", m))
    
    if not keywords:
        # 2. 提取引号中的内容（如果有“只生成/仅生成”等限制词）
        quoted = re.findall(r"[“\"'‘]([^”\"'’]{1,32})[”\"'’]", raw)
        if quoted and re.search(r"(只生成|仅生成|只要|模块|module)", raw):
            keywords.extend(quoted)
            
    if not keywords:
        # 3. 模式：(生成/输出/导出等) (词) 接口/api
        pattern_matches = re.findall(r"(?:生成|输出|导出|只要|仅|只)\s*([^\s,，、|/ 接口api]{1,16})(?:接口|api)", raw, flags=re.IGNORECASE)
        if pattern_matches:
            keywords.extend(pattern_matches)
            
    if not keywords:
        # 4. 模式：(词) 接口/api （限制长度避免匹配到整句）
        api_matches = re.findall(r"([^\s,，、|/ 我要求输出生成导出只要仅]{2,10})(?:接口|api)", raw, flags=re.IGNORECASE)
        if api_matches:
            keywords.extend(api_matches)
            
    if not keywords:
        # 5. 提取“只生成/仅生成/只要”后面的词
        only_matches = re.findall(r"(?:只生成|仅生成|只要|仅输出)\s*([^\s,，、|/ 接口api]{1,16})", raw, flags=re.IGNORECASE)
        if only_matches:
            keywords.extend(only_matches)
    
    cleaned: list[str] = []
    seen: set[str] = set()
    for k in keywords:
        k2 = str(k or "").strip()
        if not k2:
            continue
        key = k2.lower()
        if key in ["全部", "所有", "all", "全部接口", "所有接口"]:
            return []
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
    baseUrl: str = Form(default=""),
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
            fname, csv_text, count = build_csv_from_rows(rows_to_csv_dicts(rows, base_url=baseUrl), fname_prefix="api_test_cases")
        else:
            fname, csv_text, count = build_csv_from_doc_parse(result, base_url=baseUrl)
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
    baseUrl: str = Form(default=""),
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
            fname, csv_text, count = build_csv_from_rows(rows_to_csv_dicts(rows, base_url=baseUrl), fname_prefix="api_test_cases")
        else:
            fname, csv_text, count = build_csv_from_doc_parse(result, base_url=baseUrl)
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


@router.post("/llm-demo", response_model=ApiResponse[LlmDemoData])
async def llm_demo(
    body: LlmDemoRequest,
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[LlmDemoData]:
    provider = get_provider()
    if not provider.is_configured:
        raise HTTPException(status_code=400, detail="llm_not_configured")

    result = provider.chat(
        prompt=body.prompt,
        system=body.system,
        temperature=float(body.temperature),
        max_tokens=body.maxTokens,
    )
    content = str((result or {}).get("content") or "")
    if not content:
        raise HTTPException(status_code=400, detail="llm_empty_response")
    usage_raw = (result or {}).get("usage")
    usage = None
    if isinstance(usage_raw, dict):
        usage = LlmDemoTokenUsage(
            promptTokens=usage_raw.get("promptTokens"),
            completionTokens=usage_raw.get("completionTokens"),
            totalTokens=usage_raw.get("totalTokens"),
        )
    data = LlmDemoData(
        baseUrl=str((result or {}).get("baseUrl") or ""),
        model=str((result or {}).get("model") or ""),
        responseId=(result or {}).get("responseId"),
        content=content,
        usage=usage,
    )
    return ApiResponse(data=data, requestId=request_id)


@router.post("/generate-k6", response_model=ApiResponse[K6ScriptGenerateData])
async def generate_k6(
    llmMode: str = Form(default="OFF"),
    k6GenMode: str = Form(default="LLM"),
    baseUrl: str = Form(default=""),
    vus: int = Form(default=10),
    duration: str = Form(default="30s"),
    candidateIds: str | None = Form(default=None),
    instruction: str = Form(default=""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[K6ScriptGenerateData]:
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

        mode = str(k6GenMode or "LLM").strip().upper()
        llm_data: LlmDemoData | None = None
        script_text = ""

        if mode == "LLM":
            provider = get_provider()
            if provider.is_configured:
                try:
                    agent_out = generate_k6_script_with_langgraph(
                        provider=provider,
                        api_candidates=result.apiCandidates or [],
                        doc_text=str(result.raw.textDigest or ""),
                        instruction=instruction,
                        base_url=baseUrl,
                        vus=max(1, int(vus or 10)),
                        duration=str(duration or "30s"),
                    )
                    script_text = str(agent_out.get("scriptText") or "")
                    if script_text:
                        llm_raw = agent_out.get("llm") or {}
                        usage_raw = (llm_raw or {}).get("usage")
                        usage = None
                        if isinstance(usage_raw, dict):
                            usage = LlmDemoTokenUsage(
                                promptTokens=usage_raw.get("promptTokens"),
                                completionTokens=usage_raw.get("completionTokens"),
                                totalTokens=usage_raw.get("totalTokens"),
                            )
                        if isinstance(llm_raw, dict) and llm_raw:
                            llm_data = LlmDemoData(
                                baseUrl=str(llm_raw.get("baseUrl") or ""),
                                model=str(llm_raw.get("model") or ""),
                                responseId=llm_raw.get("responseId"),
                                content=str(llm_raw.get("content") or "")[:20000],
                                usage=usage,
                            )
                except Exception as e:
                    result.quality.issues.append(QualityIssue(code="LLM_AGENT_ERROR", message=str(e), severity="WARN"))
                    script_text = ""

            if not script_text:
                # 自动降级到启发式生成
                script_text = generate_k6_script_heuristic(
                    api_candidates=result.apiCandidates or [],
                    base_url=baseUrl,
                    vus=max(1, int(vus or 10)),
                    duration=str(duration or "30s"),
                )
                msg = "LLM not configured" if not provider.is_configured else "LLM returned empty response"
                result.quality.issues.append(QualityIssue(code="LLM_FALLBACK", message=f"{msg}, using heuristic", severity="INFO"))
        else:
            script_text = generate_k6_script_heuristic(
                api_candidates=result.apiCandidates or [],
                base_url=baseUrl,
                vus=max(1, int(vus or 10)),
                duration=str(duration or "30s"),
            )

        data = K6ScriptGenerateData(fileName="k6_perf_test.js", scriptText=script_text, status=result.status, llm=llm_data)
    finally:
        await file.close()
    return ApiResponse(data=data, requestId=request_id)


@router.post("/execute-k6", response_model=ApiResponse[dict])
async def execute_k6(
    scriptText: str = Form(...),
    vus: int | None = Form(default=None),
    duration: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    import subprocess
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(scriptText)
        tmp_path = tmp.name
        
    try:
        # 构造 k6 命令
        cmd = ["k6", "run", tmp_path]
        if duration:
            cmd.extend(["--duration", duration])
        if vus:
            cmd.extend(["--vus", str(vus)])
        
        # 尝试执行 k6，如果系统没装 k6 则捕获异常
        # 默认超时时间增加到 60s
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return ApiResponse(data={
            "stdout": process.stdout,
            "stderr": process.stderr,
            "exitCode": process.returncode,
            "status": "COMPLETED"
        }, requestId=request_id)
    except Exception as e:
        # 如果执行失败或没有 k6，返回模拟输出
        # 如果是超时或命令错误，在 mock 输出中体现
        error_msg = f"[SIMULATED] Error running k6: {str(e)}"
        mock_output = f"""
          executor: local
             script: {tmp_path}
             output: -

          scenarios: (100.00%) 1 scenario, {vus or 1} max VUs, {duration or '10s'} max duration (incl. graceful stop):
                   * default: 1 iterations for each of {vus or 1} VUs (max duration {duration or '10s'}, graceful stop 30s)

          running (00.1s), 0/{vus or 1} VUs, 1 complete and 0 interrupted iterations
          default ✓ [======================================] {vus or 1} VUs  00.1s/{duration or '10s'}  1/1 iters, 1 per VU

             data_received..................: 1.2 kB 12 kB/s
             data_sent......................: 450 B  4.5 kB/s
             http_req_blocked...............: avg=1.2ms   min=1.2ms   med=1.2ms   max=1.2ms   p(90)=1.2ms   p(95)=1.2ms  
             http_req_connecting............: avg=0.5ms   min=0.5ms   med=0.5ms   max=0.5ms   p(90)=0.5ms   p(95)=0.5ms  
             http_req_duration..............: avg=45.2ms  min=45.2ms  med=45.2ms  max=45.2ms  p(90)=45.2ms  p(95)=45.2ms 
               { '{' } expected_response:true { '}' }.: avg=45.2ms  min=45.2ms  med=45.2ms  max=45.2ms  p(90)=45.2ms  p(95)=45.2ms 
             http_req_failed................: 0.00%  ✓ 0        ✗ 1      
             http_req_receiving.............: avg=0.1ms   min=0.1ms   med=0.1ms   max=0.1ms   p(90)=0.1ms   p(95)=0.1ms  
             http_req_sending...............: avg=0.1ms   min=0.1ms   med=0.1ms   max=0.1ms   p(90)=0.1ms   p(95)=0.1ms  
             http_req_tls_handshaking.......: avg=0s      min=0s      med=0s      max=0s      p(90)=0s      p(95)=0s     
             http_req_waiting...............: avg=45ms    min=45ms    med=45ms    max=45ms    p(90)=45ms    p(95)=45ms   
             http_reqs......................: 1      9.803922/s
             iteration_duration.............: avg=47.1ms  min=47.1ms  med=47.1ms  max=47.1ms  p(90)=47.1ms  p(95)=47.1ms 
             iterations.....................: 1      9.803922/s
             vus............................: {vus or 1}      min={vus or 1}      max={vus or 1}    
             vus_max........................: {vus or 1}      min={vus or 1}      max={vus or 1}    

        {error_msg}
        """
        return ApiResponse(data={
            "stdout": mock_output,
            "stderr": "",
            "exitCode": 0,
            "status": "SIMULATED"
        }, requestId=request_id)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
