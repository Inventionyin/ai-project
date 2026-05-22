from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.models.enums import ArtifactType, RunStatus, TriggerType
from app.models.project import Project
from app.models.run import Artifact, Run
from app.schemas.common import ApiResponse, PageData
from app.schemas.ui_test import (
    UiTestFailedCase,
    UiTestGenerateRunData,
    UiTestGenerateRunRequest,
    UiTestReportDetailData,
    UiTestReportListItem,
    UiTestSummary,
)

router = APIRouter(prefix="/ui-tests")

_ASSERT_LEVELS = {"P0", "P1", "P2"}
_WORKSPACE_ROOT = Path(__file__).resolve().parents[5]
_FRONTEND_ROOT = _WORKSPACE_ROOT / "ai-project_front_end"
_MANIFEST_PATH = _WORKSPACE_ROOT / "docs" / "figma" / "manifest.json"
_GENERATED_SPEC_DIR = _FRONTEND_ROOT / "tests" / "ui" / "generated"
_REPORT_DIR = _FRONTEND_ROOT / "tests" / "ui" / "reports" / "html"


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _to_unix_ts(dt: datetime | None) -> int:
    if dt is None:
        return int(datetime.utcnow().timestamp())
    return int(dt.timestamp())


def _normalize_assert_level(raw: str) -> str:
    value = str(raw or "").strip().upper()
    if value not in _ASSERT_LEVELS:
        raise HTTPException(status_code=400, detail="assertLevel must be one of P0/P1/P2")
    return value


def _load_manifest() -> dict[str, Any]:
    if not _MANIFEST_PATH.exists():
        raise HTTPException(status_code=404, detail="manifest_not_found")
    try:
        return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="manifest_invalid_json") from exc


def _find_manifest_page(manifest: dict[str, Any], page_id: str) -> dict[str, Any]:
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        raise HTTPException(status_code=422, detail="manifest_pages_invalid")
    for page in pages:
        if isinstance(page, dict) and str(page.get("id") or "").strip() == page_id:
            return page
    raise HTTPException(status_code=404, detail="page_not_found")


def _resolve_page_doc(page: dict[str, Any]) -> Path:
    page_doc = str(page.get("pageDoc") or "").strip()
    if not page_doc:
        raise HTTPException(status_code=422, detail="pageDoc_required")
    full_path = (_WORKSPACE_ROOT / page_doc).resolve()
    if not full_path.exists():
        raise HTTPException(status_code=422, detail="pageDoc_not_found")
    return full_path


def _extract_section_text(content: str, section_title: str) -> str:
    marker = f"## {section_title}"
    start = content.find(marker)
    if start < 0:
        return ""
    rest = content[start + len(marker) :]
    match = re.search(r"\n##\s+", rest)
    if not match:
        return rest
    return rest[: match.start()]


def _extract_p0_texts(page_doc_text: str) -> list[str]:
    section = _extract_section_text(page_doc_text, "页面固定字段（P0）")
    if not section:
        return []
    values = re.findall(r"-\s*text:\s*(.+)", section)
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        if not value or value.startswith("REPLACE_"):
            continue
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def _build_ui_spec(*, page_id: str, route_path: str, assert_level: str, p0_texts: list[str]) -> str:
    escaped_route = route_path.replace("\\", "\\\\").replace("/", "\\/")
    lines = [
        "import { expect, test } from '@playwright/test'",
        "",
        f"test.describe('{page_id} {assert_level} 验证', () => {{",
        "  test('页面关键元素校验', async ({ page }) => {",
        f"    await page.goto('{route_path}')",
        "",
        f"    await expect(page).toHaveURL(/^{escaped_route}$/)",
    ]
    for text in p0_texts:
        escaped = text.replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"    await expect(page.getByText('{escaped}', {{ exact: true }})).toBeVisible()")
    lines.extend(
        [
            "  })",
            "})",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_playwright_summary(output_text: str) -> UiTestSummary:
    text = str(output_text or "")
    def _extract_count(keyword: str) -> int:
        m = re.search(rf"(\d+)\s+{keyword}", text, flags=re.IGNORECASE)
        return int(m.group(1)) if m else 0

    passed = _extract_count("passed")
    failed = _extract_count("failed")
    skipped = _extract_count("skipped")
    duration_ms = 0
    duration_match = re.search(r"(\d+(?:\.\d+)?)\s*(ms|s|m)\b", text, flags=re.IGNORECASE)
    if duration_match:
        value = float(duration_match.group(1))
        unit = duration_match.group(2).lower()
        if unit == "ms":
            duration_ms = int(value)
        elif unit == "s":
            duration_ms = int(value * 1000)
        elif unit == "m":
            duration_ms = int(value * 60 * 1000)
    total = passed + failed + skipped
    return UiTestSummary(total=total, passed=passed, failed=failed, skipped=skipped, durationMs=max(0, duration_ms))


async def _run_playwright(*, spec_relative_path: str, headed: bool) -> tuple[int, str, str]:
    script_name = "test:e2e:headed" if headed else "test:e2e"
    cmd = ["npm", "run", script_name, "--", spec_relative_path]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(_FRONTEND_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await process.communicate()
    return process.returncode, stdout_b.decode("utf-8", errors="replace"), stderr_b.decode("utf-8", errors="replace")


def _update_manifest_ui_automation(
    *,
    manifest: dict[str, Any],
    page: dict[str, Any],
    spec_relative_path: str,
    run_result: str,
) -> None:
    page["uiAutomation"] = {
        "status": "verified" if run_result == "PASSED" else "failed",
        "specPath": f"ai-project_front_end/{spec_relative_path.replace(os.sep, '/')}",
        "reportDir": "ai-project_front_end/tests/ui/reports/html",
        "lastRunAt": datetime.now(timezone.utc).isoformat(),
        "lastResult": run_result,
    }
    manifest["updatedAt"] = datetime.now(timezone.utc).isoformat()
    _MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _extract_ui_result(summary_json: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(summary_json, dict):
        return {}
    ui_result = summary_json.get("uiResult")
    if isinstance(ui_result, dict):
        return ui_result
    return {}


def _build_summary_from_ui_result(ui_result: dict[str, Any]) -> UiTestSummary:
    summary_raw = ui_result.get("summary")
    if isinstance(summary_raw, dict):
        return UiTestSummary(
            total=int(summary_raw.get("total") or 0),
            passed=int(summary_raw.get("passed") or 0),
            failed=int(summary_raw.get("failed") or 0),
            skipped=int(summary_raw.get("skipped") or 0),
            durationMs=int(summary_raw.get("durationMs") or 0),
        )
    return UiTestSummary(total=0, passed=0, failed=0, skipped=0, durationMs=0)


def _normalize_result(raw: str | None, run_status: RunStatus) -> str:
    value = str(raw or "").strip().upper()
    if value in {"PASSED", "FAILED", "PARTIAL", "ERROR"}:
        return value
    return "PASSED" if run_status == RunStatus.PASSED else "FAILED"


def _normalize_status(raw: str | None, run_status: RunStatus) -> str:
    value = str(raw or "").strip().upper()
    if value in {"QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELED"}:
        return value
    return "COMPLETED" if run_status == RunStatus.PASSED else "FAILED"


def _build_report_index_url(run_id: str) -> str:
    return f"/api/ui-tests/reports/{run_id}/index.html"


async def _persist_run(
    *,
    db: AsyncSession,
    user: CurrentUser,
    project_uuid: uuid.UUID,
    payload: UiTestGenerateRunRequest,
    result_status: str,
    summary: UiTestSummary,
    spec_relative_path: str,
) -> str:
    now = datetime.utcnow()
    run = Run(
        tenant_id=user.tenant_id,
        project_id=project_uuid,
        suite_id=None,
        env_id=None,
        trigger_type=TriggerType.MANUAL,
        status=RunStatus.PASSED if result_status == "PASSED" else RunStatus.FAILED,
        start_at=now,
        end_at=now,
        summary_json={
            "executionSource": "UI_AUTOMATION",
            "uiResult": {
                "pageId": payload.pageId,
                "assertLevel": payload.assertLevel,
                "status": "COMPLETED" if result_status == "PASSED" else "FAILED",
                "result": result_status,
                "reportDir": str(_REPORT_DIR),
                "specPath": f"ai-project_front_end/{spec_relative_path.replace(os.sep, '/')}",
                "summary": summary.model_dump(),
            },
        },
        created_by=user.id,
    )
    db.add(run)
    await db.flush()
    report_index = _REPORT_DIR / "index.html"
    report_size = report_index.stat().st_size if report_index.exists() else None
    artifact = Artifact(
        tenant_id=user.tenant_id,
        run_id=run.id,
        case_run_id=None,
        type=ArtifactType.LOG_BUNDLE,
        storage_url=str(_REPORT_DIR),
        size=report_size,
        meta_json={
            "kind": "UI_TEST_REPORT",
            "pageId": payload.pageId,
            "assertLevel": payload.assertLevel,
            "result": result_status,
        },
    )
    db.add(artifact)
    await db.commit()
    return str(run.id)


@router.post("/generate-and-run", response_model=ApiResponse[UiTestGenerateRunData])
async def generate_and_run_ui_test(
    payload: UiTestGenerateRunRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestGenerateRunData]:
    started_at = _now_ms()
    assert_level = _normalize_assert_level(payload.assertLevel)
    payload.assertLevel = assert_level

    try:
        project_uuid = uuid.UUID(payload.projectId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid projectId") from exc
    project = await db.get(Project, project_uuid)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    manifest = _load_manifest()
    page = _find_manifest_page(manifest, payload.pageId)
    route_path = str(page.get("routePath") or "").strip()
    if not route_path.startswith("/"):
        raise HTTPException(status_code=422, detail="routePath_invalid")

    page_doc = _resolve_page_doc(page)
    page_doc_text = page_doc.read_text(encoding="utf-8")
    p0_texts = _extract_p0_texts(page_doc_text)
    if not p0_texts:
        raise HTTPException(status_code=422, detail="p0_texts_missing")

    _GENERATED_SPEC_DIR.mkdir(parents=True, exist_ok=True)
    spec_relative_path = str(Path("tests/ui/generated") / f"{payload.pageId}.spec.ts")
    spec_full_path = _FRONTEND_ROOT / spec_relative_path
    spec_content = _build_ui_spec(
        page_id=payload.pageId,
        route_path=route_path,
        assert_level=assert_level,
        p0_texts=p0_texts,
    )
    spec_full_path.write_text(spec_content, encoding="utf-8")

    try:
        return_code, stdout_text, stderr_text = await _run_playwright(
            spec_relative_path=spec_relative_path,
            headed=payload.headed,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="npm_not_found") from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"playwright_startup_failed: {exc}") from exc
    summary = _parse_playwright_summary(f"{stdout_text}\n{stderr_text}")
    result = "PASSED" if return_code == 0 else "FAILED"
    status = "COMPLETED" if return_code == 0 else "FAILED"

    if payload.updateManifest:
        _update_manifest_ui_automation(
            manifest=manifest,
            page=page,
            spec_relative_path=spec_relative_path,
            run_result=result,
        )

    try:
        run_id = await _persist_run(
            db=db,
            user=user,
            project_uuid=project_uuid,
            payload=payload,
            result_status=result,
            summary=summary,
            spec_relative_path=spec_relative_path,
        )
    except Exception:
        await db.rollback()
        raise

    finished_at = _now_ms()
    response_data = UiTestGenerateRunData(
        runId=run_id,
        status=status,
        result=result,
        pageId=payload.pageId,
        assertLevel=assert_level,
        specPath=f"ai-project_front_end/{spec_relative_path.replace(os.sep, '/')}",
        reportDir="ai-project_front_end/tests/ui/reports/html",
        reportIndexUrl="/api/ui-tests/reports/index.html",
        summary=summary,
        startedAt=started_at,
        finishedAt=finished_at,
        stdout=stdout_text,
        stderr=stderr_text,
    )
    return ApiResponse(data=response_data, requestId=request_id)


@router.get("/reports", response_model=ApiResponse[PageData[UiTestReportListItem]])
async def list_ui_test_reports(
    projectId: str,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=200),
    status: str | None = Query(default=None),
    result: str | None = Query(default=None),
    pageId: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[UiTestReportListItem]]:
    try:
        project_uuid = uuid.UUID(projectId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid projectId") from exc

    query = (
        select(Artifact, Run)
        .join(Run, Run.id == Artifact.run_id)
        .where(
            (Artifact.tenant_id == user.tenant_id)
            & (Run.tenant_id == user.tenant_id)
            & (Run.project_id == project_uuid)
            & (Artifact.type == ArtifactType.LOG_BUNDLE)
            & (Artifact.case_run_id.is_(None))
        )
        .order_by(Artifact.created_at.desc())
    )
    rows = (await db.execute(query)).all()
    wanted_status = str(status or "").strip().upper()
    wanted_result = str(result or "").strip().upper()
    wanted_page_id = str(pageId or "").strip()
    filtered_items: list[UiTestReportListItem] = []
    for artifact, run in rows:
        meta = artifact.meta_json if isinstance(artifact.meta_json, dict) else {}
        if str(meta.get("kind") or "") != "UI_TEST_REPORT":
            continue
        ui_result = _extract_ui_result(run.summary_json if isinstance(run.summary_json, dict) else {})
        normalized_status = _normalize_status(ui_result.get("status"), run.status)
        normalized_result = _normalize_result(ui_result.get("result"), run.status)
        current_page_id = str(ui_result.get("pageId") or meta.get("pageId") or "")
        if wanted_status and wanted_status != normalized_status:
            continue
        if wanted_result and wanted_result != normalized_result:
            continue
        if wanted_page_id and wanted_page_id != current_page_id:
            continue
        summary = _build_summary_from_ui_result(ui_result)
        run_id = str(run.id)
        report_dir = str(ui_result.get("reportDir") or artifact.storage_url or "")
        item = UiTestReportListItem(
            runId=run_id,
            projectId=str(run.project_id),
            pageId=current_page_id or "unknown-page",
            status=normalized_status,
            result=normalized_result,
            assertLevel=str(ui_result.get("assertLevel") or meta.get("assertLevel") or "P0"),
            total=summary.total,
            passed=summary.passed,
            failed=summary.failed,
            skipped=summary.skipped,
            durationMs=summary.durationMs,
            reportDir=report_dir,
            reportIndexUrl=_build_report_index_url(run_id),
            createdAt=_to_unix_ts(artifact.created_at or run.created_at),
            finishedAt=_to_unix_ts(run.end_at or artifact.created_at or run.created_at),
        )
        filtered_items.append(item)

    total = len(filtered_items)
    start = (page - 1) * pageSize
    end = start + pageSize
    page_items = filtered_items[start:end]
    return ApiResponse(
        data=PageData[UiTestReportListItem](page=page, pageSize=pageSize, total=total, items=page_items),
        requestId=request_id,
    )


@router.get("/reports/{runId}", response_model=ApiResponse[UiTestReportDetailData])
async def get_ui_test_report_detail(
    runId: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestReportDetailData]:
    try:
        run_uuid = uuid.UUID(runId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid runId") from exc

    run = await db.get(Run, run_uuid)
    if run is None or run.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Run not found")

    query = (
        select(Artifact)
        .where(
            (Artifact.tenant_id == user.tenant_id)
            & (Artifact.run_id == run_uuid)
            & (Artifact.type == ArtifactType.LOG_BUNDLE)
            & (Artifact.case_run_id.is_(None))
        )
        .order_by(Artifact.created_at.desc())
    )
    artifacts = (await db.execute(query)).scalars().all()
    target_artifact: Artifact | None = None
    for artifact in artifacts:
        meta = artifact.meta_json if isinstance(artifact.meta_json, dict) else {}
        if str(meta.get("kind") or "") == "UI_TEST_REPORT":
            target_artifact = artifact
            break
    if target_artifact is None:
        raise HTTPException(status_code=404, detail="UI report not found")

    ui_result = _extract_ui_result(run.summary_json if isinstance(run.summary_json, dict) else {})
    summary = _build_summary_from_ui_result(ui_result)
    normalized_status = _normalize_status(ui_result.get("status"), run.status)
    normalized_result = _normalize_result(ui_result.get("result"), run.status)
    page_id = str(ui_result.get("pageId") or "unknown-page")
    report_dir = str(ui_result.get("reportDir") or target_artifact.storage_url or "")
    failed_cases: list[UiTestFailedCase] = []
    detail = UiTestReportDetailData(
        runId=str(run.id),
        projectId=str(run.project_id),
        pageId=page_id,
        status=normalized_status,
        result=normalized_result,
        assertLevel=str(ui_result.get("assertLevel") or "P0"),
        specPath=str(ui_result.get("specPath") or "unknown-spec-path"),
        reportDir=report_dir or "unknown-report-dir",
        reportIndexUrl=_build_report_index_url(str(run.id)),
        summary=summary,
        failedCases=failed_cases,
        startedAt=_to_unix_ts(run.start_at or run.created_at),
        finishedAt=_to_unix_ts(run.end_at or target_artifact.created_at or run.created_at),
    )
    return ApiResponse(data=detail, requestId=request_id)
