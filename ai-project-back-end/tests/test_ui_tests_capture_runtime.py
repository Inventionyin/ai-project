from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import ui_tests
from app.api.deps import CurrentUser
from app.schemas.ui_test import UiTestGeneratePytestPoRequest, UiTestGenerateRunRequest


def test_run_capture_script_maps_runtime_error_to_http_503(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _raise_oserror(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "node")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _raise_oserror)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            ui_tests._run_capture_script(
                page_url="http://127.0.0.1:5173/demo",
                page_id="demo",
                headed=False,
                capture_dir=Path("d:/tmp"),
            )
        )

    assert exc_info.value.status_code == 503
    assert str(exc_info.value.detail).startswith("capture_runtime_unavailable:")


def test_run_capture_script_maps_not_implemented_to_http_503(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _raise_not_implemented(*args, **kwargs):
        raise NotImplementedError("subprocess not supported")

    async def _to_thread(fn, *a, **k):
        return fn(*a, **k)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _raise_not_implemented)
    monkeypatch.setattr(asyncio, "to_thread", _to_thread)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "ok", ""))

    code, stdout, stderr = asyncio.run(
        ui_tests._run_capture_script(
            page_url="http://127.0.0.1:5173/demo",
            page_id="demo",
            headed=False,
            capture_dir=Path("d:/tmp"),
        )
    )

    assert code == 0
    assert stdout == "ok"
    assert stderr == ""


def test_run_playwright_falls_back_to_sync_subprocess_when_not_implemented(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async def _raise_not_implemented(*args, **kwargs):
        raise NotImplementedError("subprocess not supported")

    async def _to_thread(fn, *a, **k):
        return fn(*a, **k)

    monkeypatch.setattr(ui_tests, "_FRONTEND_ROOT", tmp_path)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _raise_not_implemented)
    monkeypatch.setattr(asyncio, "to_thread", _to_thread)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "ok", ""))

    monkeypatch.setattr(ui_tests, "_resolve_playwright_cmd", lambda **k: ["npm", "run", "test:e2e", "--", "tests/ui/generated/demo.spec.ts"])

    code, stdout, stderr = asyncio.run(
        ui_tests._run_playwright(spec_relative_path="tests/ui/generated/demo.spec.ts", headed=False)
    )

    assert code == 0
    assert stdout == "ok"
    assert stderr == ""


def test_resolve_playwright_cmd_falls_back_to_node_cli_when_npm_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ui_tests, "_FRONTEND_ROOT", tmp_path)
    (tmp_path / "node_modules" / "@playwright" / "test").mkdir(parents=True, exist_ok=True)
    cli = tmp_path / "node_modules" / "@playwright" / "test" / "cli.js"
    cli.write_text("console.log('ok')", encoding="utf-8")

    def _which(name: str):
        if name in {"npm", "npm.cmd", "npm.exe"}:
            return None
        if name in {"node", "node.exe"}:
            return "C:/node/node.exe"
        return None

    monkeypatch.setattr(ui_tests.shutil, "which", _which)

    cmd = ui_tests._resolve_playwright_cmd(spec_relative_path="tests/ui/generated/demo.spec.ts", headed=True)
    assert cmd[:3] == ["C:/node/node.exe", str(cli), "test"]
    assert "--headed" in cmd
    assert cmd[-1] == "tests/ui/generated/demo.spec.ts"


def test_generate_pytest_po_maps_unexpected_errors_to_http_503(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyDB:
        async def get(self, model, pk):
            return object()

    def _bad_page_id(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ui_tests, "_derive_page_id", _bad_page_id)

    payload = UiTestGeneratePytestPoRequest(
        projectId="79258614-0fe5-41b1-a68c-5504eeb586ed",
        pageUrl="http://localhost:5173/login",
        pageId="login_page",
        suiteType="smoke",
        assertLevel="P0",
        headed=False,
        forceRecapture=True,
    )
    user = CurrentUser(
        id=ui_tests.uuid.UUID("11111111-1111-1111-1111-111111111111"),
        tenant_id=ui_tests.uuid.UUID("22222222-2222-2222-2222-222222222222"),
        roles=frozenset(),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ui_tests.generate_pytest_po_from_url(payload, db=DummyDB(), user=user, request_id="req_test"))

    assert exc_info.value.status_code == 503
    assert str(exc_info.value.detail).startswith("generate_pytest_po_failed:")


def test_parse_figma_url_handles_design_link_with_backticks() -> None:
    file_key, node_id, normalized = ui_tests._parse_figma_url(
        " `https://www.figma.com/design/7gp8uybcxpI1wMH5fVGicg/Untitled?node-id=1-2578` "
    )
    assert file_key == "7gp8uybcxpI1wMH5fVGicg"
    assert node_id == "1:2578"
    assert "node-id=1-2578" in normalized


def test_normalize_env_page_url_appends_route_path() -> None:
    assert ui_tests._normalize_env_page_url("http://localhost:5173", "/login") == "http://localhost:5173/login"


def test_normalize_baseline_path_rejects_absolute_paths() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        ui_tests._normalize_baseline_path("D:/tmp/a.png")


def test_update_page_doc_for_bound_images_updates_p1_and_p2() -> None:
    original = """# 页面：login-page

## 关键区域视觉（P1）

```yaml
targets:
  - name: header
    figmaNodeId: "1:2578"
    testId: "auth-header"
    baseline: "header.png"
    maxDiffRatio: 0.01

masks:
  - testId: "auth-dynamic-time"
```

## 全页视觉（P2，可选）

- fullPage:
  - screenshotName: old.png
"""
    updated, count = ui_tests._update_page_doc_for_bound_images(
        page_doc_text=original,
        node_id="1:2578",
        biz_module="auth",
        images=[
            {"name": "login-form", "type": "region", "baselinePath": "ai-project_front_end/tests/ui/baselines/login-page/v1/login-form.png"},
            {"name": "full-page", "type": "fullPage", "baselinePath": "ai-project_front_end/tests/ui/baselines/login-page/v1/full-page.png"},
        ],
    )
    assert "name: login-form" in updated
    assert 'baseline: "login-form.png"' in updated
    assert "screenshotName: full-page.png" in updated
    assert count >= 2


def test_to_kebab_key_converts_camel_case() -> None:
    assert ui_tests._to_kebab_key("loginForm") == "login-form"
    assert ui_tests._to_kebab_key("fullPage") == "full-page"


def test_build_ui_spec_applies_masks_and_thresholds() -> None:
    spec = ui_tests._build_ui_spec(
        page_id="login-page",
        route_path="/login",
        assert_level="P2",
        p0_texts=["用户名"],
        p1_targets=[
            {"name": "login-form", "figmaNodeId": "1:2578", "testId": "auth-login-form", "baseline": "login-form.png", "maxDiffRatio": 0.01},
        ],
        baseline_version="v1",
        selectors={"loginForm": {"prefer": "testid", "testid": "login-form", "fallbackCss": ".login-form"}, "masks": [".toast"]},
        thresholds={"loginForm": {"maxDiffPixelRatio": 0.003}, "fullPage": {"maxDiffPixelRatio": 0.01}},
        p2_fullpage_screenshot="full-page.png",
    )
    assert "const masks" in spec
    assert "page.locator('.toast')" in spec
    assert "getByTestId('login-form')" in spec
    assert "maxDiffPixelRatio: 0.003" in spec
    assert "fullPage: true" in spec


def test_generate_and_run_allows_p1_when_p0_texts_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    page_doc = tmp_path / "login-page.md"
    page_doc.write_text(
        "\n".join(
            [
                "# 页面：login-page",
                "",
                "## 页面固定字段（P0）",
                "",
                "- title:",
                "  - text: REPLACE_TITLE_TEXT",
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest = {"pages": [{"id": "login-page", "routePath": "/login", "pageDoc": "docs/figma/pages/login-page.md"}]}
    monkeypatch.setattr(ui_tests, "_load_manifest", lambda: manifest)
    monkeypatch.setattr(ui_tests, "_resolve_page_doc", lambda page: page_doc)
    monkeypatch.setattr(ui_tests, "_FRONTEND_ROOT", tmp_path)
    monkeypatch.setattr(ui_tests, "_GENERATED_SPEC_DIR", tmp_path / "tests" / "ui" / "generated")

    async def _fake_run_playwright(*, spec_relative_path: str, headed: bool) -> tuple[int, str, str]:
        return 0, "1 passed", ""

    async def _fake_persist_run(*args, **kwargs) -> str:
        return "run_test"

    monkeypatch.setattr(ui_tests, "_run_playwright", _fake_run_playwright)
    monkeypatch.setattr(ui_tests, "_persist_run", _fake_persist_run)

    class DummyDB:
        async def get(self, model, pk):
            return object()

        async def rollback(self):
            return None

    payload = UiTestGenerateRunRequest(
        projectId="79258614-0fe5-41b1-a68c-5504eeb586ed",
        pageId="login-page",
        assertLevel="P1",
        headed=False,
        updateManifest=False,
    )
    user = CurrentUser(
        id=ui_tests.uuid.UUID("11111111-1111-1111-1111-111111111111"),
        tenant_id=ui_tests.uuid.UUID("22222222-2222-2222-2222-222222222222"),
        roles=frozenset(),
    )
    resp = asyncio.run(ui_tests.generate_and_run_ui_test(payload, db=DummyDB(), user=user, request_id="req_test"))
    assert resp.data is not None
    assert resp.data.assertLevel == "P1"
    assert resp.data.pageId == "login-page"
