from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
    UiBaselineBindImagesData,
    UiBaselineBindImagesRequest,
    UiBaselineInitData,
    UiBaselineInitRequest,
    UiBaselineSelectorsData,
    UiBaselineSelectorsRequest,
    UiTestFailedCase,
    UiTestGeneratePytestPoData,
    UiTestGeneratePytestPoRequest,
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
_CAPTURE_DIR = _FRONTEND_ROOT / "tests" / "ui" / "capture"
_AUTOMATION_ROOT = _WORKSPACE_ROOT / "automation_pytest"
_AUTOMATION_PAGES_DIR = _AUTOMATION_ROOT / "pages"
_AUTOMATION_TESTS_DIR = _AUTOMATION_ROOT / "tests"
_AUTOMATION_LOCATORS_DIR = _AUTOMATION_ROOT / "locators"
_SUITE_TYPES = {"smoke", "regression"}


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


def _normalize_suite_type(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value not in _SUITE_TYPES:
        raise HTTPException(status_code=400, detail="suiteType must be one of smoke/regression")
    return value


def _slugify_page_id(raw: str) -> str:
    value = str(raw or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value:
        raise HTTPException(status_code=422, detail="pageId_invalid")
    return value[:128]


def _derive_page_id(raw_page_id: str | None, page_url: str) -> str:
    value = str(raw_page_id or "").strip()
    if value:
        return _slugify_page_id(value)
    parsed = urlparse(page_url)
    path_part = str(parsed.path or "").strip("/")
    candidate = path_part.split("/")[-1] if path_part else ""
    if not candidate:
        candidate = str(parsed.netloc or "").split(":")[0]
    return _slugify_page_id(candidate or "ui-page")


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


def _extract_p1_targets(page_doc_text: str) -> list[dict[str, Any]]:
    section = _extract_section_text(page_doc_text, "关键区域视觉（P1）")
    if not section:
        return []
    block_match = re.search(r"```(?:yaml|yml)\s*([\s\S]*?)```", section, flags=re.IGNORECASE)
    if not block_match:
        return []
    raw_yaml = str(block_match.group(1) or "").strip()
    if not raw_yaml:
        return []
    try:
        import yaml

        parsed = yaml.safe_load(raw_yaml)
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    targets_raw = parsed.get("targets")
    if not isinstance(targets_raw, list):
        return []
    targets: list[dict[str, Any]] = []
    for item in targets_raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        figma_node_id = str(item.get("figmaNodeId") or "").strip()
        test_id = str(item.get("testId") or "").strip()
        baseline = str(item.get("baseline") or "").strip()
        if not name or not figma_node_id or not test_id or not baseline:
            continue
        if not baseline.lower().endswith(".png"):
            baseline = f"{baseline}.png"
        try:
            max_diff_ratio = float(item.get("maxDiffRatio") if item.get("maxDiffRatio") is not None else 0.01)
        except Exception:
            max_diff_ratio = 0.01
        max_diff_ratio = min(max(0.0, max_diff_ratio), 1.0)
        targets.append(
            {
                "name": name,
                "figmaNodeId": figma_node_id,
                "testId": test_id,
                "baseline": baseline,
                "maxDiffRatio": max_diff_ratio,
            }
        )
    return targets


def _extract_p2_fullpage_screenshot_name(page_doc_text: str) -> str:
    section = _extract_section_text(page_doc_text, "全页视觉（P2，可选）")
    if not section:
        return ""
    m = re.search(r"screenshotName:\s*([^\s]+)", section)
    if not m:
        return ""
    return str(m.group(1) or "").strip()


def _to_kebab_key(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = value.replace("_", "-")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _build_ui_spec(
    *,
    page_id: str,
    route_path: str,
    assert_level: str,
    p0_texts: list[str],
    p1_targets: list[dict[str, Any]],
    baseline_version: str,
    selectors: dict[str, Any] | None,
    thresholds: dict[str, Any] | None,
    p2_fullpage_screenshot: str,
) -> str:
    escaped_route = route_path.replace("\\", "\\\\").replace("/", "\\/")
    needs_visual = assert_level in {"P1", "P2"} and bool(p1_targets)
    needs_fullpage = assert_level == "P2" and bool(p2_fullpage_screenshot)
    def _to_js_identifier(raw: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_]", "_", str(raw or ""))
        cleaned = cleaned.strip("_") or "target"
        if cleaned[0].isdigit():
            cleaned = f"t_{cleaned}"
        return cleaned

    lines = []
    if needs_visual:
        lines.append("import { existsSync } from 'fs'")
    lines.extend(
        [
            "import { expect, test } from '@playwright/test'",
            "",
            f"test.describe('{page_id} {assert_level} 验证', () => {{",
            "  test('页面关键元素校验', async ({ page }, testInfo) => {",
            f"    await page.goto('{route_path}')",
            "",
            f"    await expect(page).toHaveURL(/{escaped_route}(?:\\?.*)?$/)",
        ]
    )
    if needs_visual:
        selector_map: dict[str, Any] = {}
        mask_selectors: list[str] = []
        if isinstance(selectors, dict):
            for k, v in selectors.items():
                if k == "masks" and isinstance(v, list):
                    mask_selectors = [str(s or "").strip() for s in v if str(s or "").strip()]
                elif isinstance(v, dict):
                    key = _to_kebab_key(k)
                    if key:
                        selector_map[key] = dict(v)
        threshold_map: dict[str, Any] = {}
        if isinstance(thresholds, dict):
            for k, v in thresholds.items():
                if isinstance(v, dict):
                    key = _to_kebab_key(k)
                    if key:
                        threshold_map[key] = dict(v)

        lines.extend(
            [
                "",
                "    await page.addStyleTag({",
                "      content: '*{animation-duration:0s!important;transition-duration:0s!important;}'",
                "    })",
            ]
        )
        if mask_selectors:
            def _js_single(raw: str) -> str:
                return str(raw or "").replace("\\", "\\\\").replace("'", "\\'")

            masks_js = ", ".join([f"page.locator('{_js_single(s)}')" for s in mask_selectors])
            lines.append(f"    const masks = [{masks_js}]")
        else:
            lines.append("    const masks = []")

        for target in p1_targets:
            test_id = str(target.get("testId") or "").strip()
            baseline = str(target.get("baseline") or "").strip()
            name = str(target.get("name") or "").strip()
            max_diff_ratio = target.get("maxDiffRatio", 0.01)
            key = _to_kebab_key(name)
            selector_rule = selector_map.get(key) if key else None
            threshold_rule = threshold_map.get(key) if key else None
            try:
                threshold_value = float(threshold_rule.get("maxDiffPixelRatio")) if isinstance(threshold_rule, dict) and threshold_rule.get("maxDiffPixelRatio") is not None else None
            except Exception:
                threshold_value = None
            effective_diff = threshold_value if threshold_value is not None else max_diff_ratio

            escaped_test_id = test_id.replace("\\", "\\\\").replace("'", "\\'")
            escaped_baseline = baseline.replace("\\", "\\\\").replace("'", "\\'")
            var_name = _to_js_identifier(name)
            snapshot_arg = f"{page_id}/{baseline_version}/{baseline}".replace("//", "/")
            escaped_snapshot = snapshot_arg.replace("\\", "\\\\").replace("'", "\\'")

            locator_lines: list[str] = []
            if isinstance(selector_rule, dict) and str(selector_rule.get("prefer") or "").strip().lower() == "testid" and str(selector_rule.get("testid") or "").strip():
                preferred_testid = str(selector_rule.get("testid") or "").strip()
                fallback_css = str(selector_rule.get("fallbackCss") or "").strip()
                preferred_testid_esc = preferred_testid.replace("\\", "\\\\").replace("'", "\\'")
                locator_lines.append(f"    const {var_name}Preferred = page.getByTestId('{preferred_testid_esc}')")
                if fallback_css:
                    fallback_css_esc = fallback_css.replace("\\", "\\\\").replace("'", "\\'")
                    locator_lines.append(f"    const {var_name}Fallback = page.locator('{fallback_css_esc}')")
                    locator_lines.append(f"    const {var_name} = (await {var_name}Preferred.count()) ? {var_name}Preferred : {var_name}Fallback")
                else:
                    locator_lines.append(f"    const {var_name} = {var_name}Preferred")
            elif isinstance(selector_rule, dict) and str(selector_rule.get("prefer") or "").strip().lower() in {"css", "selector"} and str(selector_rule.get("fallbackCss") or "").strip():
                css = str(selector_rule.get("fallbackCss") or "").strip()
                css_esc = css.replace("\\", "\\\\").replace("'", "\\'")
                locator_lines.append(f"    const {var_name} = page.locator('{css_esc}')")
            else:
                locator_lines.append(f"    const {var_name} = page.getByTestId('{escaped_test_id}')")

            lines.extend(
                [
                    "",
                    *locator_lines,
                    f"    await expect({var_name}).toBeVisible()",
                    f"    const {var_name}SnapshotName = '{escaped_snapshot}'",
                    f"    const {var_name}SnapshotPath = testInfo.snapshotPath({var_name}SnapshotName)",
                    f"    if (!existsSync({var_name}SnapshotPath)) {{",
                    f"      testInfo.annotations.push({{ type: 'missing-baseline', description: {var_name}SnapshotName }})",
                    "    } else {",
                    f"      await expect({var_name}).toHaveScreenshot({var_name}SnapshotName, {{ maxDiffPixelRatio: {effective_diff}, mask: masks }})",
                    "    }",
                ]
            )
        if needs_fullpage:
            full_key = _to_kebab_key("fullPage")
            full_threshold_rule = threshold_map.get(full_key) if full_key else None
            try:
                full_diff = float(full_threshold_rule.get("maxDiffPixelRatio")) if isinstance(full_threshold_rule, dict) and full_threshold_rule.get("maxDiffPixelRatio") is not None else 0.01
            except Exception:
                full_diff = 0.01
            full_snapshot_arg = f"{page_id}/{baseline_version}/{p2_fullpage_screenshot}".replace("//", "/")
            full_snapshot_esc = full_snapshot_arg.replace("\\", "\\\\").replace("'", "\\'")
            lines.extend(
                [
                    "",
                    f"    const fullPageSnapshotName = '{full_snapshot_esc}'",
                    "    const fullPageSnapshotPath = testInfo.snapshotPath(fullPageSnapshotName)",
                    "    if (!existsSync(fullPageSnapshotPath)) {",
                    "      testInfo.annotations.push({ type: 'missing-baseline', description: fullPageSnapshotName })",
                    "    } else {",
                    f"      await expect(page).toHaveScreenshot(fullPageSnapshotName, {{ maxDiffPixelRatio: {full_diff}, mask: masks, fullPage: true }})",
                    "    }",
                ]
            )
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


def _resolve_playwright_cmd(*, spec_relative_path: str, headed: bool) -> list[str]:
    spec_arg = str(spec_relative_path or "").replace("\\", "/")
    npm_from_env = str(os.environ.get("UI_TEST_NPM") or os.environ.get("NPM_BIN") or "").strip() or None
    npm = npm_from_env or shutil.which("npm") or shutil.which("npm.cmd") or shutil.which("npm.exe")
    if npm:
        script_name = "test:e2e:headed" if headed else "test:e2e"
        return [npm, "run", script_name, "--", spec_arg]

    node_from_env = str(os.environ.get("UI_TEST_NODE") or os.environ.get("NODE_BIN") or "").strip() or None
    node = node_from_env or shutil.which("node") or shutil.which("node.exe")
    if not node:
        raise HTTPException(status_code=503, detail="node_runtime_not_found")

    playwright_cli_from_env = str(os.environ.get("UI_TEST_PLAYWRIGHT_CLI") or "").strip() or None
    cli_path = Path(playwright_cli_from_env) if playwright_cli_from_env else (_FRONTEND_ROOT / "node_modules" / "@playwright" / "test" / "cli.js")
    if not cli_path.exists():
        raise HTTPException(status_code=503, detail="playwright_cli_not_found")

    cmd = [node, str(cli_path), "test"]
    if headed:
        cmd.append("--headed")
    cmd.append(spec_arg)
    return cmd


async def _run_playwright(*, spec_relative_path: str, headed: bool) -> tuple[int, str, str]:
    cmd = _resolve_playwright_cmd(spec_relative_path=spec_relative_path, headed=headed)
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(_FRONTEND_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await process.communicate()
        return process.returncode, stdout_b.decode("utf-8", errors="replace"), stderr_b.decode("utf-8", errors="replace")
    except NotImplementedError:
        import subprocess

        def _run_sync() -> tuple[int, str, str]:
            completed = subprocess.run(
                cmd,
                cwd=str(_FRONTEND_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return int(completed.returncode or 0), str(completed.stdout or ""), str(completed.stderr or "")

        try:
            return await asyncio.to_thread(_run_sync)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="subprocess_not_supported") from exc


async def _run_capture_script(*, page_url: str, page_id: str, headed: bool, capture_dir: Path) -> tuple[int, str, str]:
    capture_script = _FRONTEND_ROOT / "scripts" / "ui_capture.mjs"
    if not capture_script.exists():
        raise HTTPException(status_code=503, detail="capture_script_not_found")
    cmd = [
        "node",
        str(capture_script),
        "--url",
        page_url,
        "--page-id",
        page_id,
        "--out",
        str(capture_dir),
    ]
    if headed:
        cmd.append("--headed")
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(_FRONTEND_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except NotImplementedError as exc:
        try:
            import subprocess

            def _run_sync() -> tuple[int, str, str]:
                completed = subprocess.run(
                    cmd,
                    cwd=str(_FRONTEND_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                return int(completed.returncode or 0), str(completed.stdout or ""), str(completed.stderr or "")

            return await asyncio.to_thread(_run_sync)
        except Exception as fallback_exc:
            raise HTTPException(status_code=503, detail="subprocess_not_supported") from fallback_exc
    except OSError as exc:
        detail = str(exc.strerror or exc).strip() or "capture_runtime_unavailable"
        raise HTTPException(status_code=503, detail=f"capture_runtime_unavailable: {detail}"[:2000]) from exc
    stdout_b, stderr_b = await process.communicate()
    return process.returncode, stdout_b.decode("utf-8", errors="replace"), stderr_b.decode("utf-8", errors="replace")


def _build_locator(item: dict[str, Any]) -> dict[str, str]:
    test_id = str(item.get("dataTestId") or "").strip()
    role = str(item.get("role") or "").strip()
    text = str(item.get("text") or "").strip()
    aria_label = str(item.get("ariaLabel") or "").strip()
    placeholder = str(item.get("placeholder") or "").strip()
    if test_id:
        return {"strategy": "testid", "value": test_id}
    if role and text:
        return {"strategy": "role_text", "value": f"{role}|{text}"}
    if aria_label:
        return {"strategy": "label", "value": aria_label}
    if placeholder:
        return {"strategy": "placeholder", "value": placeholder}
    selector = str(item.get("selector") or "").strip()
    if selector:
        return {"strategy": "css", "value": selector}
    return {"strategy": "text", "value": text or "unknown"}


def _build_locator_name(item: dict[str, Any], index: int) -> str:
    raw = str(item.get("text") or item.get("ariaLabel") or item.get("placeholder") or item.get("tag") or "")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", raw.strip().lower()).strip("_")
    if not cleaned:
        cleaned = "element"
    return f"{cleaned}_{index}"


def _render_locator_yaml(page_id: str, elements: list[dict[str, Any]]) -> str:
    lines = [f"page_id: {page_id}", "locators:"]
    for idx, item in enumerate(elements, start=1):
        locator = _build_locator(item)
        name = _build_locator_name(item, idx)
        strategy = locator["strategy"].replace('"', '\\"')
        value = locator["value"].replace('"', '\\"')
        lines.append(f'  {name}: {{ strategy: "{strategy}", value: "{value}" }}')
    return "\n".join(lines) + "\n"


def _build_page_py(page_id: str, elements: list[dict[str, Any]]) -> str:
    class_name = "".join(part.capitalize() for part in page_id.split("-")) + "Page"
    lines = [
        "from playwright.sync_api import Page",
        "",
        f"class {class_name}:",
        "    def __init__(self, page: Page, base_url: str):",
        "        self.page = page",
        "        self.base_url = base_url.rstrip('/')",
        "",
        "    def open(self, path: str = '') -> None:",
        "        target = f\"{self.base_url}/{path.lstrip('/')}\" if path else self.base_url",
        "        self.page.goto(target, wait_until='networkidle')",
        "",
        "    def assert_loaded(self) -> None:",
    ]
    if elements:
        first_locator = _build_locator(elements[0])
        strategy = first_locator["strategy"]
        value = first_locator["value"].replace("\\", "\\\\").replace("'", "\\'")
        if strategy == "testid":
            lines.append(f"        self.page.get_by_test_id('{value}').wait_for()")
        elif strategy == "role_text":
            role, _, text = value.partition("|")
            role_v = role.replace("\\", "\\\\").replace("'", "\\'")
            text_v = text.replace("\\", "\\\\").replace("'", "\\'")
            lines.append(f"        self.page.get_by_role('{role_v}', name='{text_v}').wait_for()")
        elif strategy == "label":
            lines.append(f"        self.page.get_by_label('{value}').wait_for()")
        elif strategy == "placeholder":
            lines.append(f"        self.page.get_by_placeholder('{value}').wait_for()")
        elif strategy == "css":
            lines.append(f"        self.page.locator('{value}').first.wait_for()")
        else:
            lines.append(f"        self.page.get_by_text('{value}', exact=False).first.wait_for()")
    else:
        lines.append("        self.page.wait_for_timeout(500)")
    return "\n".join(lines) + "\n"


def _build_test_py(page_id: str, suite_type: str, assert_level: str, page_path: str) -> str:
    class_name = "".join(part.capitalize() for part in page_id.split("-")) + "Page"
    import_path = page_path.replace("\\", "/").replace("/", ".")
    if import_path.endswith(".py"):
        import_path = import_path[:-3]
    lines = [
        "import allure",
        "import pytest",
        f"from {import_path} import {class_name}",
        "",
        f"@allure.feature('{page_id}')",
        f"@allure.story('{suite_type}')",
        "@pytest.mark.ui",
        f"def test_{page_id.replace('-', '_')}_{suite_type}(page, base_url):",
        f"    target = {class_name}(page, base_url)",
        "    with allure.step('打开页面'):",
        "        target.open()",
        "    with allure.step('页面加载校验'):",
        "        target.assert_loaded()",
        "    with allure.step('断言等级标记'):",
        f"        assert '{assert_level}' in ['P0', 'P1', 'P2']",
        "",
    ]
    return "\n".join(lines)


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


def _clean_figma_url(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    match = re.search(r"https?://[^\s`]+", text)
    return str(match.group(0)) if match else text.strip("`").strip()


def _parse_figma_url(figma_url: str) -> tuple[str, str, str]:
    cleaned = _clean_figma_url(figma_url)
    parsed = urlparse(cleaned)
    host = str(parsed.netloc or "").lower()
    if not host.endswith("figma.com"):
        raise HTTPException(status_code=422, detail="figmaUrl_invalid")

    path_parts = [p for p in str(parsed.path or "").split("/") if p]
    file_key = ""
    if len(path_parts) >= 2 and path_parts[0] in {"design", "file", "proto"}:
        file_key = path_parts[1]
    if not file_key or not re.fullmatch(r"[A-Za-z0-9]+", file_key):
        raise HTTPException(status_code=422, detail="figma_fileKey_invalid")

    try:
        from urllib.parse import parse_qs

        qs = parse_qs(parsed.query or "")
    except Exception:
        qs = {}
    node_raw = ""
    if isinstance(qs, dict):
        values = qs.get("node-id") or qs.get("node_id") or []
        if isinstance(values, list) and values:
            node_raw = str(values[0] or "")
    node_raw = node_raw.strip()
    if not node_raw:
        raise HTTPException(status_code=422, detail="figma_nodeId_missing")
    if ":" in node_raw:
        node_id = node_raw
    else:
        node_id = node_raw.replace("-", ":")
    if not re.fullmatch(r"I?\d+:\d+", node_id):
        raise HTTPException(status_code=422, detail="figma_nodeId_invalid")

    normalized_url = cleaned
    if "node-id=" not in normalized_url:
        normalized_url = f"{cleaned}{'&' if parsed.query else '?'}node-id={node_raw}"
    return file_key, node_id, normalized_url


def _normalize_env_page_url(env_url: str, route_path: str) -> str:
    raw_env = str(env_url or "").strip()
    raw_route = str(route_path or "").strip()
    if not raw_route.startswith("/"):
        raise HTTPException(status_code=422, detail="routePath_invalid")
    parsed = urlparse(raw_env)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="envUrl_invalid")
    current_path = str(parsed.path or "").rstrip("/")
    if current_path and current_path.endswith(raw_route.rstrip("/")):
        return raw_env.rstrip("/")
    base = raw_env.rstrip("/")
    return f"{base}{raw_route}"


def _normalize_baseline_path(raw: str) -> str:
    value = str(raw or "").strip().replace("\\", "/")
    if not value:
        raise HTTPException(status_code=422, detail="baselinePath_invalid")
    if re.match(r"^[a-zA-Z]:/", value) or value.startswith("//"):
        raise HTTPException(status_code=422, detail="baselinePath_must_be_relative")
    if ".." in value.split("/"):
        raise HTTPException(status_code=422, detail="baselinePath_invalid")
    return value


def _extract_markdown_code_block(content: str, section_title: str) -> tuple[str, int, int]:
    section = _extract_section_text(content, section_title)
    if not section:
        return "", -1, -1
    block_match = re.search(r"```(?:yaml|yml)\s*([\s\S]*?)```", section, flags=re.IGNORECASE)
    if not block_match:
        return "", -1, -1
    section_start = content.find(f"## {section_title}")
    if section_start < 0:
        return "", -1, -1
    block_start = section_start + len(f"## {section_title}") + block_match.start(0)
    block_end = section_start + len(f"## {section_title}") + block_match.end(0)
    return str(block_match.group(1) or ""), block_start, block_end


def _update_page_doc_for_bound_images(
    *,
    page_doc_text: str,
    node_id: str,
    biz_module: str,
    images: list[dict[str, Any]],
) -> tuple[str, int]:
    text = str(page_doc_text or "")
    updated = 0

    region_images = [it for it in images if str(it.get("type") or "").strip().lower() in {"region", "p1"}]
    full_images = [it for it in images if str(it.get("type") or "").strip().lower() in {"fullpage", "p2", "full-page"}]

    if region_images:
        yaml_body, block_start, block_end = _extract_markdown_code_block(text, "关键区域视觉（P1）")
        if block_start >= 0 and block_end >= 0:
            existing_yaml = yaml_body.strip("\n")
            if "targets:" not in existing_yaml:
                existing_yaml = "targets:\n" + existing_yaml + ("\n" if existing_yaml else "")
            insert_pos = existing_yaml.find("masks:")
            before = existing_yaml if insert_pos < 0 else existing_yaml[:insert_pos].rstrip("\n")
            after = "" if insert_pos < 0 else "\n" + existing_yaml[insert_pos:].lstrip("\n")

            for item in region_images:
                name = str(item.get("name") or "").strip()
                baseline_path = str(item.get("baselinePath") or "").strip()
                if not name or not baseline_path:
                    continue
                baseline_file = baseline_path.replace("\\", "/").split("/")[-1]
                name_key = name.strip().lower()
                pattern = rf"(^\s*-\s*name:\s*{re.escape(name_key)}\s*$)"
                if re.search(pattern, before, flags=re.IGNORECASE | re.MULTILINE):
                    def _replace_baseline(m: re.Match) -> str:
                        return m.group(0)

                    before2 = re.sub(
                        rf"(^\s*-\s*name:\s*{re.escape(name)}\s*$[\s\S]*?^\s*baseline:\s*\")([^\"]+)(\"\s*$)",
                        rf"\1{baseline_file}\3",
                        before,
                        flags=re.IGNORECASE | re.MULTILINE,
                    )
                    if before2 != before:
                        before = before2
                        updated += 1
                    continue

                figma_node_id = str(item.get("figmaNodeId") or node_id).strip() or node_id
                test_id = str(item.get("testId") or f"{biz_module}-{name}").strip()
                before = (
                    before.rstrip("\n")
                    + "\n"
                    + "\n".join(
                        [
                            f"  - name: {name}",
                            f'    figmaNodeId: "{figma_node_id}"',
                            f'    testId: "{test_id}"',
                            f'    baseline: "{baseline_file}"',
                            "    maxDiffRatio: 0.01",
                        ]
                    )
                    + "\n"
                )
                updated += 1

            new_yaml = (before.rstrip("\n") + ("\n" if before and not before.endswith("\n") else "") + after.lstrip("\n")).strip("\n")
            fenced = "```yaml\n" + new_yaml + "\n```"
            new_section = text[:block_start] + fenced + text[block_end:]
            if new_section != text:
                text = new_section

    if full_images:
        baseline_path = str(full_images[0].get("baselinePath") or "").strip()
        if baseline_path:
            baseline_file = baseline_path.replace("\\", "/").split("/")[-1]
            section_title = "全页视觉（P2，可选）"
            marker = f"## {section_title}"
            start = text.find(marker)
            if start >= 0:
                rest = text[start:]
                if re.search(r"^\s*-\s*screenshotName:\s*", rest, flags=re.MULTILINE):
                    new_rest = re.sub(
                        r"(^\s*-\s*screenshotName:\s*).*$",
                        rf"\1{baseline_file}",
                        rest,
                        count=1,
                        flags=re.MULTILINE,
                    )
                    if new_rest != rest:
                        text = text[:start] + new_rest
                        updated += 1
                else:
                    insertion = f"{marker}\n\n- fullPage:\n  - screenshotName: {baseline_file}\n"
                    end_section = text.find("\n## ", start + len(marker))
                    if end_section < 0:
                        text = text[:start] + insertion
                    else:
                        text = text[:start] + insertion + text[end_section:]
                    updated += 1
            else:
                text = text.rstrip() + "\n\n" + marker + "\n\n- fullPage:\n  - screenshotName: " + baseline_file + "\n"
                updated += 1

    return text, updated


def _render_page_doc_template(
    *,
    page_id: str,
    biz_module: str,
    route_path: str,
    file_key: str,
    node_id: str,
    baseline_dir: str,
    baseline_version: str,
) -> str:
    template_path = (_WORKSPACE_ROOT / "docs" / "figma" / "pages" / "_template.md").resolve()
    if not template_path.exists():
        raise HTTPException(status_code=503, detail="page_doc_template_missing")
    text = template_path.read_text(encoding="utf-8")
    design_version = baseline_version[1:] if str(baseline_version).lower().startswith("v") else str(baseline_version)
    rendered = (
        text.replace("REPLACE_PAGE_ID", page_id)
        .replace("REPLACE_BIZ_MODULE", biz_module)
        .replace("REPLACE_ROUTE_PATH", route_path)
        .replace("REPLACE_FILE_KEY", file_key)
        .replace("REPLACE_NODE_ID", node_id)
        .replace("REPLACE_DESIGN_VERSION", design_version)
        .replace("ai-project_front_end/tests/ui/baseline/REPLACE_PAGE_ID", baseline_dir)
    )
    node_for_filename = node_id.replace(":", "-")
    rendered = re.sub(
        r'^(?P<prefix>\s*baseline:\s*")(?P<name>[^"]+)(?P<suffix>"\s*)$',
        lambda m: f'{m.group("prefix")}{m.group("name").replace(node_id, node_for_filename)}{m.group("suffix")}',
        rendered,
        flags=re.MULTILINE,
    )
    return rendered


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
    report_size = None
    if report_index.exists():
        try:
            report_size = report_index.stat().st_size
        except OSError:
            report_size = None
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


@router.post("/baseline/init", response_model=ApiResponse[UiBaselineInitData])
async def init_ui_baseline_config(
    payload: UiBaselineInitRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiBaselineInitData]:
    try:
        project_uuid = uuid.UUID(payload.projectId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid projectId") from exc
    project = await db.get(Project, project_uuid)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    action = str(payload.action or "").strip()
    if action and action != "ui-baseline:init":
        raise HTTPException(status_code=422, detail="action_invalid")

    page_id = _slugify_page_id(payload.pageId)
    route_path = str(payload.routePath or "").strip()
    env_page_url = _normalize_env_page_url(payload.envUrl, route_path)
    baseline_version = str(payload.baselineVersion or "v1").strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", baseline_version):
        raise HTTPException(status_code=422, detail="baselineVersion_invalid")

    file_key, node_id, figma_url = _parse_figma_url(payload.figmaUrl)
    biz_module = (route_path.strip("/").split("/", maxsplit=1)[0] or page_id.split("-", maxsplit=1)[0] or "ui").strip()

    baseline_dir = f"ai-project_front_end/tests/ui/baseline/{page_id}"
    page_doc_rel = f"docs/figma/pages/{page_id}.md"
    page_doc_path = (_WORKSPACE_ROOT / page_doc_rel).resolve()
    try:
        (_WORKSPACE_ROOT / "docs" / "figma" / "pages").mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        detail = str(exc.strerror or exc).strip() or "page_doc_dir_unavailable"
        raise HTTPException(status_code=503, detail=f"page_doc_dir_unavailable: {detail}"[:2000]) from exc

    if not page_doc_path.exists():
        content = _render_page_doc_template(
            page_id=page_id,
            biz_module=biz_module,
            route_path=route_path,
            file_key=file_key,
            node_id=node_id,
            baseline_dir=baseline_dir,
            baseline_version=baseline_version,
        )
        try:
            page_doc_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            detail = str(exc.strerror or exc).strip() or "page_doc_write_failed"
            raise HTTPException(status_code=503, detail=f"page_doc_write_failed: {detail}"[:2000]) from exc

    manifest = _load_manifest()
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        raise HTTPException(status_code=422, detail="manifest_pages_invalid")

    existing_page: dict[str, Any] | None = None
    for it in pages:
        if isinstance(it, dict) and str(it.get("id") or "").strip() == page_id:
            existing_page = it
            break
    target = existing_page if existing_page is not None else {}
    target.update(
        {
            "id": page_id,
            "bizModule": biz_module,
            "figmaUrl": figma_url,
            "fileKey": file_key,
            "nodeId": node_id,
            "routePath": route_path,
            "envUrl": env_page_url,
            "pageDoc": page_doc_rel,
            "baselineDir": baseline_dir,
            "baselineVersion": baseline_version,
            "render": payload.render.model_dump() if payload.render is not None else None,
            "status": str(target.get("status") or "pending"),
            "tags": list(dict.fromkeys([*([str(t) for t in (target.get("tags") or [])] if isinstance(target.get("tags"), list) else []), "P0", biz_module])),
        }
    )
    if existing_page is None:
        pages.append(target)

    manifest["updatedAt"] = datetime.now(timezone.utc).isoformat()
    try:
        _MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"manifest_write_failed: {type(exc).__name__}") from exc

    data = UiBaselineInitData(
        pageId=page_id,
        manifestPath=str(_MANIFEST_PATH.relative_to(_WORKSPACE_ROOT)).replace("\\", "/"),
        pageDoc=page_doc_rel,
        baselineDir=baseline_dir,
    )
    return ApiResponse(data=data, requestId=request_id)


@router.post("/baseline/bind-images", response_model=ApiResponse[UiBaselineBindImagesData])
async def bind_ui_baseline_images(
    payload: UiBaselineBindImagesRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiBaselineBindImagesData]:
    action = str(payload.action or "").strip()
    if action and action != "ui-baseline:bind-images":
        raise HTTPException(status_code=422, detail="action_invalid")

    page_id = _slugify_page_id(payload.pageId)
    baseline_version = str(payload.baselineVersion or "v1").strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", baseline_version):
        raise HTTPException(status_code=422, detail="baselineVersion_invalid")

    images_payload: list[dict[str, Any]] = []
    for it in payload.images or []:
        images_payload.append(
            {
                "name": str(it.name or "").strip(),
                "type": str(it.type or "").strip(),
                "baselinePath": _normalize_baseline_path(it.baselinePath),
            }
        )

    manifest = _load_manifest()
    page = _find_manifest_page(manifest, page_id)
    biz_module = str(page.get("bizModule") or "").strip() or "ui"
    node_id = str(page.get("nodeId") or "").strip() or "0:0"

    baseline_images = page.get("baselineImages")
    if not isinstance(baseline_images, dict):
        baseline_images = {}
    baseline_images[baseline_version] = images_payload
    page["baselineImages"] = baseline_images

    page_doc = _resolve_page_doc(page)
    page_doc_text = page_doc.read_text(encoding="utf-8")
    updated_text, updated_count = _update_page_doc_for_bound_images(
        page_doc_text=page_doc_text,
        node_id=node_id,
        biz_module=biz_module,
        images=images_payload,
    )
    if updated_text != page_doc_text:
        try:
            page_doc.write_text(updated_text, encoding="utf-8")
        except OSError as exc:
            detail = str(exc.strerror or exc).strip() or "page_doc_write_failed"
            raise HTTPException(status_code=503, detail=f"page_doc_write_failed: {detail}"[:2000]) from exc

    manifest["updatedAt"] = datetime.now(timezone.utc).isoformat()
    try:
        _MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"manifest_write_failed: {type(exc).__name__}") from exc

    data = UiBaselineBindImagesData(
        pageId=page_id,
        baselineVersion=baseline_version,
        pageDoc=str(page_doc.relative_to(_WORKSPACE_ROOT)).replace("\\", "/"),
        updatedCount=int(updated_count),
    )
    return ApiResponse(data=data, requestId=request_id)


@router.post("/baseline/selectors", response_model=ApiResponse[UiBaselineSelectorsData])
async def update_ui_baseline_selectors(
    payload: UiBaselineSelectorsRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiBaselineSelectorsData]:
    action = str(payload.action or "").strip()
    if action and action != "ui-baseline:selectors":
        raise HTTPException(status_code=422, detail="action_invalid")

    page_id = _slugify_page_id(payload.pageId)
    manifest = _load_manifest()
    page = _find_manifest_page(manifest, page_id)

    selectors_dump = payload.selectors.model_dump()
    selectors_dump["masks"] = [str(s or "").strip() for s in (payload.selectors.masks or []) if str(s or "").strip()]
    page["selectors"] = selectors_dump
    if payload.thresholds is not None:
        page["thresholds"] = payload.thresholds.model_dump()

    updated_at = datetime.now(timezone.utc).isoformat()
    manifest["updatedAt"] = updated_at
    try:
        _MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"manifest_write_failed: {type(exc).__name__}") from exc

    data = UiBaselineSelectorsData(pageId=page_id, updatedAt=updated_at)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/generate-pytest-po", response_model=ApiResponse[UiTestGeneratePytestPoData])
async def generate_pytest_po_from_url(
    payload: UiTestGeneratePytestPoRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[UiTestGeneratePytestPoData]:
    try:
        project_uuid = uuid.UUID(payload.projectId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid projectId") from exc
    project = await db.get(Project, project_uuid)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        page_url = str(payload.pageUrl or "").strip()
        parsed_url = urlparse(page_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise HTTPException(status_code=422, detail="pageUrl_invalid")
        page_id = _derive_page_id(payload.pageId, page_url)
        suite_type = _normalize_suite_type(payload.suiteType)
        assert_level = _normalize_assert_level(payload.assertLevel)
        capture_dir = _CAPTURE_DIR / page_id
        elements_path = capture_dir / "elements.json"
        screenshot_path = capture_dir / "page.png"
        reused_capture = False
        if elements_path.exists() and screenshot_path.exists() and not payload.forceRecapture:
            reused_capture = True
        else:
            try:
                capture_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                detail = str(exc.strerror or exc).strip() or "capture_dir_unavailable"
                raise HTTPException(status_code=503, detail=f"capture_dir_unavailable: {detail}"[:2000]) from exc
            code, stdout_text, stderr_text = await _run_capture_script(
                page_url=page_url,
                page_id=page_id,
                headed=payload.headed,
                capture_dir=capture_dir,
            )
            if code != 0:
                detail = f"capture_failed: {stderr_text or stdout_text or 'unknown_error'}"
                raise HTTPException(status_code=503, detail=detail[:2000])
        if not elements_path.exists():
            raise HTTPException(status_code=503, detail="elements_file_missing")
        try:
            raw_elements = json.loads(elements_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=422, detail="elements_json_invalid") from exc
        if not isinstance(raw_elements, list):
            raise HTTPException(status_code=422, detail="elements_json_invalid")
        elements: list[dict[str, Any]] = [item for item in raw_elements if isinstance(item, dict)]
        try:
            _AUTOMATION_PAGES_DIR.mkdir(parents=True, exist_ok=True)
            _AUTOMATION_TESTS_DIR.mkdir(parents=True, exist_ok=True)
            _AUTOMATION_LOCATORS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            detail = str(exc.strerror or exc).strip() or "automation_dir_unavailable"
            raise HTTPException(status_code=503, detail=f"automation_dir_unavailable: {detail}"[:2000]) from exc
        page_file = _AUTOMATION_PAGES_DIR / f"{page_id}_page.py"
        test_file = _AUTOMATION_TESTS_DIR / f"test_{page_id}_{suite_type}.py"
        locators_file = _AUTOMATION_LOCATORS_DIR / f"{page_id}.yaml"
        page_py = _build_page_py(page_id, elements)
        try:
            page_file.write_text(page_py, encoding="utf-8")
        except OSError as exc:
            detail = str(exc.strerror or exc).strip() or "page_file_write_failed"
            raise HTTPException(status_code=503, detail=f"page_file_write_failed: {detail}"[:2000]) from exc
        try:
            page_import = str(page_file.relative_to(_WORKSPACE_ROOT)).replace("\\", "/")
        except ValueError as exc:
            raise HTTPException(status_code=503, detail="page_path_outside_workspace") from exc
        test_py = _build_test_py(page_id, suite_type, assert_level, page_import)
        try:
            test_file.write_text(test_py, encoding="utf-8")
        except OSError as exc:
            detail = str(exc.strerror or exc).strip() or "test_file_write_failed"
            raise HTTPException(status_code=503, detail=f"test_file_write_failed: {detail}"[:2000]) from exc
        locator_yaml = _render_locator_yaml(page_id, elements)
        try:
            locators_file.write_text(locator_yaml, encoding="utf-8")
        except OSError as exc:
            detail = str(exc.strerror or exc).strip() or "locators_file_write_failed"
            raise HTTPException(status_code=503, detail=f"locators_file_write_failed: {detail}"[:2000]) from exc
        try:
            capture_dir_rel = str(capture_dir.relative_to(_WORKSPACE_ROOT)).replace("\\", "/")
            elements_path_rel = str(elements_path.relative_to(_WORKSPACE_ROOT)).replace("\\", "/")
            screenshot_path_rel = str(screenshot_path.relative_to(_WORKSPACE_ROOT)).replace("\\", "/")
            test_file_rel = str(test_file.relative_to(_WORKSPACE_ROOT)).replace("\\", "/")
            page_file_rel = str(page_file.relative_to(_WORKSPACE_ROOT)).replace("\\", "/")
            locators_file_rel = str(locators_file.relative_to(_WORKSPACE_ROOT)).replace("\\", "/")
        except ValueError as exc:
            raise HTTPException(status_code=503, detail="artifact_path_outside_workspace") from exc
        response_data = UiTestGeneratePytestPoData(
            pageId=page_id,
            suiteType=suite_type,
            assertLevel=assert_level,
            captureDir=capture_dir_rel,
            elementsPath=elements_path_rel,
            screenshotPath=screenshot_path_rel,
            testPath=test_file_rel,
            pagePath=page_file_rel,
            locatorsPath=locators_file_rel,
            commandHint=f"pytest automation_pytest/tests/test_{page_id}_{suite_type}.py --alluredir=automation_pytest/allure-results",
            elementCount=len(elements),
            reusedCapture=reused_capture,
        )
        return ApiResponse(data=response_data, requestId=request_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"generate_pytest_po_failed: {type(exc).__name__}") from exc


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
    baseline_version = str(page.get("baselineVersion") or "v1").strip() or "v1"
    selectors = page.get("selectors") if isinstance(page.get("selectors"), dict) else {}
    thresholds = page.get("thresholds") if isinstance(page.get("thresholds"), dict) else {}

    page_doc = _resolve_page_doc(page)
    page_doc_text = page_doc.read_text(encoding="utf-8")
    p0_texts = _extract_p0_texts(page_doc_text)
    if assert_level == "P0" and not p0_texts:
        raise HTTPException(status_code=422, detail="p0_texts_missing")
    p1_targets = _extract_p1_targets(page_doc_text)
    p2_fullpage = _extract_p2_fullpage_screenshot_name(page_doc_text)

    _GENERATED_SPEC_DIR.mkdir(parents=True, exist_ok=True)
    spec_relative = Path("tests") / "ui" / "generated" / f"{payload.pageId}.spec.ts"
    spec_relative_path = spec_relative.as_posix()
    spec_full_path = _FRONTEND_ROOT / spec_relative
    spec_content = _build_ui_spec(
        page_id=payload.pageId,
        route_path=route_path,
        assert_level=assert_level,
        p0_texts=p0_texts,
        p1_targets=p1_targets,
        baseline_version=baseline_version,
        selectors=selectors,
        thresholds=thresholds,
        p2_fullpage_screenshot=p2_fullpage,
    )
    try:
        spec_full_path.write_text(spec_content, encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"spec_write_failed: {type(exc).__name__}") from exc

    try:
        return_code, stdout_text, stderr_text = await _run_playwright(
            spec_relative_path=spec_relative_path,
            headed=payload.headed,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail="subprocess_not_supported") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="npm_not_found") from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"playwright_startup_failed: {exc}") from exc
    summary = _parse_playwright_summary(f"{stdout_text}\n{stderr_text}")
    result = "PASSED" if return_code == 0 else "FAILED"
    status = "COMPLETED" if return_code == 0 else "FAILED"

    if payload.updateManifest:
        try:
            _update_manifest_ui_automation(
                manifest=manifest,
                page=page,
                spec_relative_path=spec_relative_path,
                run_result=result,
            )
        except OSError as exc:
            raise HTTPException(status_code=503, detail=f"manifest_write_failed: {type(exc).__name__}") from exc

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
