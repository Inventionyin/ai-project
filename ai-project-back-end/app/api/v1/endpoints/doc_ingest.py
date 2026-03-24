from __future__ import annotations

import json
from typing import Iterable
import re
import logging
import shutil

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
from datetime import datetime

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
from app.models.project import Project
from app.models.testcase import TestCase
from app.models.enums import TestCaseType, Priority, TestCaseStatus

logger = logging.getLogger(__name__)

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
    
    # 1. 提取模块/module 后面的内容
    module_matches = re.findall(r"(?:模块|module)\s*[：:]\s*([^\n;；。!！?？]+)", raw, flags=re.IGNORECASE)
    for m in module_matches:
        keywords.extend(re.split(r"[,，、|/ \s]+", m))
    
    # 2. 提取引号中的内容（如果有“只生成/仅生成”等限制词）
    quoted = re.findall(r"[“\"'‘]([^”\"'’]{1,32})[”\"'’]", raw)
    if quoted and re.search(r"(只生成|仅生成|只要|模块|module|生成)", raw):
        keywords.extend(quoted)
            
    # 3. 模式：(生成/输出/导出等) (词) 接口/api
    pattern_matches = re.findall(r"(?:生成|输出|导出|只要|仅|只)\s*([^\s,，、|/ 接口api]{1,16})(?:接口|api)", raw, flags=re.IGNORECASE)
    if pattern_matches:
        keywords.extend(pattern_matches)
            
    # 4. 模式：(词) 接口/api （限制长度避免匹配到整句）
    api_matches = re.findall(r"([^\s,，、|/ 我要求输出生成导出只要仅]{2,10})(?:接口|api)", raw, flags=re.IGNORECASE)
    if api_matches:
        keywords.extend(api_matches)
            
    # 5. 提取“只生成/仅生成/只要/生成”等动词后面的具体内容
    # 特别处理“生成 登录 Logout 测试用例”这种场景
    if not keywords:
        verb_matches = re.findall(r"(?:生成|只生成|仅生成|只要|仅输出|导出|针对|对于)\s*([^\n;；。!！?？]+)", raw, flags=re.IGNORECASE)
        for m in verb_matches:
            # 移除结尾的常见后缀
            m_cleaned = re.sub(r"(?:测试用例|用例|接口|api|的内容|的所有内容|的全部内容)$", "", m.strip(), flags=re.IGNORECASE).strip()
            # 进一步移除“模块”和“的”前缀/后缀
            m_cleaned = re.sub(r"模块的?$", "", m_cleaned).strip()
            # 如果还有内容，则按分隔符拆分
            if m_cleaned:
                parts = re.split(r"[,，、|/ \s]+", m_cleaned)
                for p in parts:
                    p = p.strip()
                    if p:
                        keywords.append(p)
    
    cleaned: list[str] = []
    seen: set[str] = set()
    for k in keywords:
        k2 = str(k or "").strip()
        if not k2:
            continue
        key = k2.lower()
        if key in ["全部", "所有", "all", "全部接口", "所有接口", "全部内容", "所有内容"]:
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
        
        # 优化：如果 caseGenMode 为 AUTO/LLM 但 llmMode 为 OFF，自动开启增强模式以提取 API
        effective_llm_mode = llmMode
        if str(caseGenMode or "").strip().upper() in ("AUTO", "LLM") and str(llmMode or "").strip().upper() == "OFF":
            effective_llm_mode = "AUTO"
            
        result = apply_llm_enhancement(result, effective_llm_mode)
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
        
        # 优化：如果 caseGenMode 为 AUTO/LLM 但 llmMode 为 OFF，自动开启增强模式以提取 API
        effective_llm_mode = llmMode
        if str(caseGenMode or "").strip().upper() in ("AUTO", "LLM") and str(llmMode or "").strip().upper() == "OFF":
            effective_llm_mode = "AUTO"
            
        result = apply_llm_enhancement(result, effective_llm_mode)
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
    projectId: str = Form(...),
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
    pid = uuid.UUID(projectId)
    # 获取项目信息
    project = await db.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read()
    try:
        result = parse_document(content, file.filename or "unknown", job_id=None)
        
        # 优化：如果 k6GenMode 为 LLM 但 llmMode 为 OFF，自动开启增强模式以提取 API
        effective_llm_mode = llmMode
        if str(k6GenMode or "").strip().upper() == "LLM" and str(llmMode or "").strip().upper() == "OFF":
            effective_llm_mode = "AUTO"
            
        result = apply_llm_enhancement(result, effective_llm_mode)
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

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 移除非法字符，保留项目名称
        safe_project_name = re.sub(r'[\\/:*?"<>|]', '_', project.name)
        file_name = f"k6_{safe_project_name}_{timestamp}.js"
        
        # 保存到物理目录
        save_dir = os.path.join("testcase", "k6")
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(script_text)

        # 保存到数据库
        testcase = TestCase(
            tenant_id=user.tenant_id,
            project_id=pid,
            title=f"k6_perf_{safe_project_name}_{timestamp}",
            type=TestCaseType.PERF,
            priority=Priority.P1,
            status=TestCaseStatus.DRAFT,
            content_md=script_text,
            ai_meta_json={
                "vus": vus,
                "duration": duration,
                "baseUrl": baseUrl,
                "instruction": instruction,
                "fileName": file_name,
                "k6GenMode": mode
            },
            generated_by_ai=True,
            owner_id=user.id,
            created_by=user.id
        )
        db.add(testcase)
        await db.commit()
        await db.refresh(testcase)

        data = K6ScriptGenerateData(
            fileName=file_name, 
            scriptText=script_text, 
            status=result.status, 
            llm=llm_data,
            testcaseId=str(testcase.id),
            testcaseTitle=testcase.title
        )
    except Exception:
        await db.rollback()
        raise
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
    import asyncio
    import tempfile
    import os
    import re
    import traceback
    import sys
    import subprocess
    from app.services.doc_ingest.monitor import SystemMonitor
    
    # 预检 k6 是否存在
    k6_path = shutil.which("k6")
    if not k6_path:
        return ApiResponse(data={
            "stdout": "[ERROR] k6 executable not found. Please install k6 and add it to your PATH.",
            "stderr": "",
            "exitCode": -1,
            "status": "FAILED"
        }, requestId=request_id)

    logger.info(f"[{request_id}] Starting k6 execution for user {user.id}")
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(scriptText)
        tmp_path = tmp.name
        
    # 计算执行超时时间
    timeout_sec = 60 # 默认 60s
    if duration:
        m = re.match(r"(\d+)([smh])", duration)
        if m:
            val, unit = m.groups()
            val = int(val)
            if unit == "s":
                timeout_sec = val
            elif unit == "m":
                timeout_sec = val * 60
            elif unit == "h":
                timeout_sec = val * 3600
        else:
            try:
                # 尝试直接转为数字
                timeout_sec = int(duration)
            except:
                pass
                
    # 给 k6 留出启动和生成报告的时间（30s 缓冲）
    run_timeout = timeout_sec + 30
    
    monitor = SystemMonitor()
        
    try:
        # 构造 k6 命令
        cmd = [k6_path, "run", tmp_path]
        if duration:
            cmd.extend(["--duration", duration])
        if vus:
            cmd.extend(["--vus", str(vus)])
        
        logger.info(f"[{request_id}] Command: {' '.join(cmd)}")
        
        # 开启系统监控
        await monitor.start()
        
        # 使用 asyncio.create_subprocess_exec 避免阻塞事件循环
        # 这样后端可以同时处理 k6 发起的 HTTP 请求
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info(f"[{request_id}] k6 process started with PID {process.pid}")
        except NotImplementedError:
            # Windows SelectorEventLoop 兼容性修复 (当 ProactorEventLoop 未能成功设置时)
            logger.warning(f"[{request_id}] asyncio.create_subprocess_exec not implemented, falling back to sync subprocess in thread")
            
            # 在单独线程中同步运行以避免阻塞主循环
            def run_sync():
                p = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                try:
                    # 使用 communicate() 等待进程完成并获取输出
                    out, err = p.communicate(timeout=run_timeout)
                    return p.returncode, out, err
                except subprocess.TimeoutExpired:
                    p.kill()
                    out, err = p.communicate()
                    return -1, out + "\n[ERROR] Execution timeout expired", err
                except Exception as e:
                    return -1, f"[ERROR] Subprocess error: {str(e)}", ""

            # 启动监控并在线程中执行
            await monitor.start()
            returncode, stdout_str, stderr_str = await asyncio.to_thread(run_sync)
            await monitor.stop()
            report = monitor.generate_report()
            
            report_text = ""
            if isinstance(report, dict) and "cpu" in report:
                report_text = (
                    f"\n\n{'='*20} 服务器性能报告 (Fallback) {'='*20}\n"
                    f"采样次数: {report['sample_count']}\n"
                    f"执行时长: {report['duration_seconds']:.2f}s\n"
                    f"CPU 使用率: 平均 {report['cpu']['avg']:.1f}%, 最大 {report['cpu']['max']:.1f}%\n"
                    f"内存使用率: 平均 {report['memory']['avg']:.1f}%, 最大 {report['memory']['max']:.1f}%\n"
                    f"{'='*56}\n"
                )
            
            return ApiResponse(data={
                "stdout": stdout_str + report_text,
                "stderr": stderr_str,
                "exitCode": returncode,
                "status": "COMPLETED" if returncode == 0 else "FAILED",
                "monitorReport": report
            }, requestId=request_id)
        
        stdout_chunks = []
        stderr_chunks = []

        async def read_stream(stream, chunks, prefix="", out_file=None):
            if out_file is None:
                out_file = sys.stdout
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace")
                chunks.append(decoded)
                # 同步输出到终端
                out_file.write(f"{prefix}{decoded}")
                out_file.flush()

        try:
            # 并发读取 stdout 和 stderr
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(process.stdout, stdout_chunks, prefix="[k6-stdout] ", out_file=sys.stdout),
                    read_stream(process.stderr, stderr_chunks, prefix="[k6-stderr] ", out_file=sys.stderr)
                ),
                timeout=run_timeout
            )
            await process.wait()
            
            # 停止监控并生成报告
            await monitor.stop()
            report = monitor.generate_report()
            
            logger.info(f"[{request_id}] k6 execution completed with exit code {process.returncode}")
            
            report_text = ""
            if "cpu" in report:
                report_text = (
                    f"\n\n{'='*20} 服务器性能报告 {'='*20}\n"
                    f"采样次数: {report['sample_count']}\n"
                    f"执行时长: {report['duration_seconds']:.2f}s\n"
                    f"CPU 使用率: 平均 {report['cpu']['avg']:.1f}%, 最大 {report['cpu']['max']:.1f}%\n"
                    f"内存使用率: 平均 {report['memory']['avg']:.1f}%, 最大 {report['memory']['max']:.1f}%\n"
                    f"{'='*56}\n"
                )
            
            return ApiResponse(data={
                "stdout": "".join(stdout_chunks) + report_text,
                "stderr": "".join(stderr_chunks),
                "exitCode": process.returncode,
                "status": "COMPLETED",
                "monitorReport": report
            }, requestId=request_id)
        except asyncio.TimeoutError:
            # 如果超时，尝试终止进程
            await monitor.stop()
            try:
                process.kill()
            except:
                pass
            
            report = monitor.generate_report()
            report_text = ""
            if "cpu" in report:
                report_text = (
                    f"\n\n{'='*20} 服务器性能报告 (超时) {'='*20}\n"
                    f"采样次数: {report['sample_count']}\n"
                    f"执行时长: {report['duration_seconds']:.2f}s\n"
                    f"CPU 使用率: 平均 {report['cpu']['avg']:.1f}%, 最大 {report['cpu']['max']:.1f}%\n"
                    f"内存使用率: 平均 {report['memory']['avg']:.1f}%, 最大 {report['memory']['max']:.1f}%\n"
                    f"{'='*60}\n"
                )
                
            return ApiResponse(data={
                "stdout": f"[ERROR] Command timed out after {run_timeout}s\n" + "".join(stdout_chunks) + report_text,
                "stderr": "".join(stderr_chunks),
                "exitCode": -1,
                "status": "TIMEOUT",
                "monitorReport": report
            }, requestId=request_id)
            
    except (FileNotFoundError, NotImplementedError, OSError) as e:
        await monitor.stop()
        # NotImplementedError 通常在 Windows 上使用 SelectorEventLoop 时发生
        # OSError 可能包含具体的系统错误码
        is_missing = isinstance(e, FileNotFoundError) or \
                    (isinstance(e, OSError) and getattr(e, 'errno', None) == 2)
        
        err_msg = f"k6 executable not found on system. Please install k6 to run performance tests. Error: {str(e)}" if is_missing else f"System error during k6 startup: {str(e)}"
        
        return ApiResponse(data={
            "stdout": f"[ERROR] {err_msg}\n{traceback.format_exc()}",
            "stderr": "",
            "exitCode": -1,
            "status": "FAILED"
        }, requestId=request_id)
    except Exception as e:
        # 其他异常
        return ApiResponse(data={
            "stdout": f"[ERROR] Error running k6: {str(e)} ({type(e).__name__})\n{traceback.format_exc()}",
            "stderr": "",
            "exitCode": -1,
            "status": "FAILED"
        }, requestId=request_id)
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
