from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.project import Project
from app.models.ui_automation import UiTestRun, UiTestScript
from app.schemas.ui_automation import UiTestRunDetail, UiTestScriptDetail


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_script_detail(row: UiTestScript) -> UiTestScriptDetail:
    return UiTestScriptDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        name=row.name,
        description=row.description or "",
        scriptType=row.script_type,
        scriptContent=row.script_content or "",
        recordingJson=dict(row.recording_json) if row.recording_json else {},
        status=row.status,
        browser=row.browser,
        viewportWidth=row.viewport_width,
        viewportHeight=row.viewport_height,
        baseUrl=row.base_url or "",
        tags=list(row.tags) if row.tags else [],
        createdBy=str(row.created_by) if row.created_by else None,
        createdAt=int(row.created_at.timestamp()) if row.created_at else 0,
        updatedAt=int(row.updated_at.timestamp()) if row.updated_at else 0,
    )


def _to_run_detail(row: UiTestRun) -> UiTestRunDetail:
    return UiTestRunDetail(
        id=str(row.id),
        scriptId=str(row.script_id),
        status=row.status,
        startedAt=row.started_at,
        finishedAt=row.finished_at,
        durationMs=row.duration_ms,
        stepsTotal=row.steps_total,
        stepsPassed=row.steps_passed,
        stepsFailed=row.steps_failed,
        screenshotPaths=list(row.screenshot_paths) if row.screenshot_paths else [],
        errorMessage=row.error_message,
        tracePath=row.trace_path,
        reportPath=row.report_path,
        createdAt=int(row.created_at.timestamp()) if row.created_at else 0,
        updatedAt=int(row.updated_at.timestamp()) if row.updated_at else 0,
    )


async def _get_project(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> Project:
    project = await db.scalar(
        select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def create_script(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    name: str, description: str = "", script_type: str = "PLAYWRIGHT",
    browser: str = "chromium", viewport_width: int = 1280, viewport_height: int = 720,
    base_url: str = "", tags: list[str] | None = None,
) -> UiTestScriptDetail:
    await _get_project(db, user=user, project_id=project_id)
    row = UiTestScript(
        tenant_id=user.tenant_id,
        project_id=project_id,
        name=name,
        description=description,
        script_type=script_type,
        browser=browser,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        base_url=base_url,
        tags=tags or [],
        created_by=user.id,
    )
    db.add(row)
    await db.flush()
    return _to_script_detail(row)


async def list_scripts(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    page: int = 1, page_size: int = 20,
) -> tuple[int, list[UiTestScriptDetail]]:
    await _get_project(db, user=user, project_id=project_id)
    base = select(UiTestScript).where(
        UiTestScript.tenant_id == user.tenant_id,
        UiTestScript.project_id == project_id,
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(
        base.order_by(desc(UiTestScript.created_at)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return total, [_to_script_detail(r) for r in rows]


async def get_script(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, script_id: uuid.UUID,
) -> UiTestScriptDetail:
    await _get_project(db, user=user, project_id=project_id)
    row = await db.scalar(select(UiTestScript).where(
        UiTestScript.id == script_id,
        UiTestScript.project_id == project_id,
        UiTestScript.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return _to_script_detail(row)


async def update_script(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, script_id: uuid.UUID,
    **kwargs,
) -> UiTestScriptDetail:
    await _get_project(db, user=user, project_id=project_id)
    row = await db.scalar(select(UiTestScript).where(
        UiTestScript.id == script_id,
        UiTestScript.project_id == project_id,
        UiTestScript.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Script not found")
    for key, value in kwargs.items():
        if value is not None:
            if key == "name":
                row.name = value
            elif key == "description":
                row.description = value
            elif key == "script_type":
                row.script_type = value
            elif key == "browser":
                row.browser = value
            elif key == "viewport_width":
                row.viewport_width = value
            elif key == "viewport_height":
                row.viewport_height = value
            elif key == "base_url":
                row.base_url = value
            elif key == "tags":
                row.tags = value
    await db.flush()
    return _to_script_detail(row)


async def delete_script(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, script_id: uuid.UUID,
) -> None:
    await _get_project(db, user=user, project_id=project_id)
    row = await db.scalar(select(UiTestScript).where(
        UiTestScript.id == script_id,
        UiTestScript.project_id == project_id,
        UiTestScript.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Script not found")
    await db.delete(row)
    await db.flush()


async def save_recording(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    script_id: uuid.UUID, actions: list[dict],
) -> UiTestScriptDetail:
    await _get_project(db, user=user, project_id=project_id)
    row = await db.scalar(select(UiTestScript).where(
        UiTestScript.id == script_id,
        UiTestScript.project_id == project_id,
        UiTestScript.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Script not found")
    row.recording_json = {"actions": actions}
    row.status = "RECORDED"
    await db.flush()
    return _to_script_detail(row)


def generate_playwright_script(recording: dict, config: dict) -> str:
    """Convert recorded actions to a Playwright test script."""
    base_url = config.get("baseUrl", "")
    viewport_w = config.get("viewportWidth", 1280)
    viewport_h = config.get("viewportHeight", 720)

    actions = recording.get("actions", [])

    lines = [
        'import { test, expect } from "@playwright/test";',
        "",
        f'test.describe("Recorded Test", () => {{',
        f'  test("recorded flow", async ({{ page }}) => {{',
        f"    await page.setViewportSize({{ width: {viewport_w}, height: {viewport_h} }});",
        f'    await page.goto("{base_url}");',
        "",
    ]

    for action in actions:
        action_type = action.get("type", "")
        selector = action.get("selector", "")
        value = action.get("value", "")

        if action_type == "click":
            lines.append(f'    await page.click("{selector}");')
        elif action_type == "fill":
            lines.append(f'    await page.fill("{selector}", "{value}");')
        elif action_type == "navigate":
            lines.append(f'    await page.goto("{value}");')
        elif action_type == "assert":
            lines.append(f'    await expect(page.locator("{selector}")).{value};')
        elif action_type == "wait":
            lines.append(f'    await page.waitForSelector("{selector}");')
        elif action_type == "screenshot":
            lines.append(f'    await page.screenshot({{ path: "{value}" }});')

    lines.extend([
        "  });",
        "});",
        "",
    ])

    return "\n".join(lines)


async def generate_script(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, script_id: uuid.UUID,
) -> UiTestScriptDetail:
    await _get_project(db, user=user, project_id=project_id)
    row = await db.scalar(select(UiTestScript).where(
        UiTestScript.id == script_id,
        UiTestScript.project_id == project_id,
        UiTestScript.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Script not found")

    recording = dict(row.recording_json) if row.recording_json else {}
    if not recording.get("actions"):
        raise HTTPException(status_code=400, detail="No recorded actions found. Record actions first.")

    config = {
        "baseUrl": row.base_url,
        "browser": row.browser,
        "viewportWidth": row.viewport_width,
        "viewportHeight": row.viewport_height,
    }
    script_content = generate_playwright_script(recording, config)
    row.script_content = script_content
    row.status = "READY"
    await db.flush()
    return _to_script_detail(row)


async def run_ui_test(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, script_id: uuid.UUID,
) -> UiTestRunDetail:
    await _get_project(db, user=user, project_id=project_id)
    script = await db.scalar(select(UiTestScript).where(
        UiTestScript.id == script_id,
        UiTestScript.project_id == project_id,
        UiTestScript.tenant_id == user.tenant_id,
    ))
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    if not script.script_content:
        raise HTTPException(status_code=400, detail="Script has no content. Generate the script first.")

    recording = dict(script.recording_json) if script.recording_json else {}
    actions = recording.get("actions", [])

    started = _now_iso()
    run = UiTestRun(
        tenant_id=user.tenant_id,
        script_id=script_id,
        status="RUNNING",
        started_at=started,
        steps_total=len(actions),
    )
    db.add(run)
    script.status = "RUNNING"
    await db.flush()

    try:
        import asyncio
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            spec_path = Path(tmp_dir) / "recorded.spec.ts"
            spec_path.write_text(script.script_content, encoding="utf-8")

            process = await asyncio.create_subprocess_exec(
                "npx", "playwright", "test", str(spec_path),
                "--reporter=json",
                cwd=str(Path(__file__).resolve().parents[3] / "ai-project_front_end"),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await process.communicate()
            stdout = stdout_b.decode("utf-8", errors="replace")
            stderr = stderr_b.decode("utf-8", errors="replace")

        finished = _now_iso()
        import json as json_mod
        try:
            result = json_mod.loads(stdout)
            stats = result.get("stats", {})
            expected = stats.get("expected", 0)
            unexpected = stats.get("unexpected", 0)
            skipped = stats.get("skipped", 0)
            duration = stats.get("duration", 0)
            run.steps_passed = expected
            run.steps_failed = unexpected
            run.status = "PASSED" if unexpected == 0 and expected > 0 else "FAILED"
            run.duration_ms = duration
        except Exception:
            run.steps_passed = 0
            run.steps_failed = run.steps_total
            run.status = "PASSED" if process.returncode == 0 else "FAILED"
            run.duration_ms = 0

        run.finished_at = finished
        run.error_message = stderr[:5000] if run.status == "FAILED" else None
        script.status = run.status

    except FileNotFoundError:
        run.status = "ERROR"
        run.finished_at = _now_iso()
        run.error_message = "npx or playwright not found. Ensure Playwright is installed."
        script.status = "READY"
    except Exception as exc:
        run.status = "ERROR"
        run.finished_at = _now_iso()
        run.error_message = str(exc)[:5000]
        script.status = "READY"

    await db.flush()
    return _to_run_detail(run)


async def list_runs(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    script_id: uuid.UUID | None = None, page: int = 1, page_size: int = 20,
) -> tuple[int, list[UiTestRunDetail]]:
    await _get_project(db, user=user, project_id=project_id)
    base = select(UiTestRun).where(
        UiTestRun.tenant_id == user.tenant_id,
    )
    if script_id:
        base = base.where(UiTestRun.script_id == script_id)
    else:
        script_ids = select(UiTestScript.id).where(
            UiTestScript.tenant_id == user.tenant_id,
            UiTestScript.project_id == project_id,
        )
        base = base.where(UiTestRun.script_id.in_(script_ids))

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(
        base.order_by(desc(UiTestRun.created_at)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return total, [_to_run_detail(r) for r in rows]


async def get_run(
    db: AsyncSession, *, user: CurrentUser, run_id: uuid.UUID,
) -> UiTestRunDetail:
    row = await db.scalar(select(UiTestRun).where(
        UiTestRun.id == run_id,
        UiTestRun.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_run_detail(row)
