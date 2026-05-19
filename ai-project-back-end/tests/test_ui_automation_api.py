from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import ui_automation as ui_automation_endpoint
from app.core.database import get_db
from app.schemas.ui_automation import UiTestScriptDetail


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_SCRIPT_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
_RUN_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(
        ui_automation_endpoint.router,
        prefix="/api",
    )

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=_USER_ID,
            tenant_id=_TENANT_ID,
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def _make_script_detail(name: str = "Login Test", browser: str = "chromium") -> UiTestScriptDetail:
    return UiTestScriptDetail(
        id=str(_SCRIPT_ID),
        projectId=str(_PROJECT_ID),
        name=name,
        description="",
        scriptType="PLAYWRIGHT",
        scriptContent="",
        recordingJson={},
        status="DRAFT",
        browser=browser,
        viewportWidth=1280,
        viewportHeight=720,
        baseUrl="",
        tags=[],
        createdBy=str(_USER_ID),
        createdAt=1710000000,
        updatedAt=1710000000,
    )


def test_create_ui_script(monkeypatch) -> None:
    async def _fake_create(db, *, user, project_id, name, description="", script_type="PLAYWRIGHT",
                           browser="chromium", viewport_width=1280, viewport_height=720,
                           base_url="", tags=None):
        return _make_script_detail(name=name, browser=browser)

    monkeypatch.setattr(ui_automation_endpoint, "create_script", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/ui-automation/scripts",
        json={"name": "Login Test", "browser": "chromium", "projectId": str(_PROJECT_ID)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Login Test"
    assert body["data"]["browser"] == "chromium"


def test_create_ui_script_firefox(monkeypatch) -> None:
    async def _fake_create(db, *, user, project_id, name, description="", script_type="PLAYWRIGHT",
                           browser="chromium", viewport_width=1280, viewport_height=720,
                           base_url="", tags=None):
        return _make_script_detail(name=name, browser=browser)

    monkeypatch.setattr(ui_automation_endpoint, "create_script", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/ui-automation/scripts",
        json={"name": "Checkout Test", "browser": "firefox", "projectId": str(_PROJECT_ID)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Checkout Test"
    assert body["data"]["browser"] == "firefox"


def test_list_ui_scripts_empty(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id, page, page_size):
        return (0, [])

    monkeypatch.setattr(ui_automation_endpoint, "list_scripts", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/ui-automation/scripts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_list_ui_scripts_with_data(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id, page, page_size):
        return (1, [_make_script_detail()])

    monkeypatch.setattr(ui_automation_endpoint, "list_scripts", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/ui-automation/scripts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "Login Test"


def test_get_ui_script(monkeypatch) -> None:
    async def _fake_get(db, *, user, project_id, script_id):
        return _make_script_detail()

    monkeypatch.setattr(ui_automation_endpoint, "get_script", _fake_get)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/ui-automation/scripts/{_SCRIPT_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["id"] == str(_SCRIPT_ID)


def test_update_ui_script(monkeypatch) -> None:
    async def _fake_update(db, *, user, project_id, script_id, name=None, description=None,
                           script_type=None, browser=None, viewport_width=None,
                           viewport_height=None, base_url=None, tags=None):
        return _make_script_detail(name=name or "Updated")

    monkeypatch.setattr(ui_automation_endpoint, "update_script", _fake_update)

    client = TestClient(_build_app())
    resp = client.put(
        f"/api/projects/{_PROJECT_ID}/ui-automation/scripts/{_SCRIPT_ID}",
        json={"name": "Updated Script"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Updated Script"


def test_delete_ui_script(monkeypatch) -> None:
    async def _fake_delete(db, *, user, project_id, script_id):
        return None

    monkeypatch.setattr(ui_automation_endpoint, "delete_script", _fake_delete)

    client = TestClient(_build_app())
    resp = client.delete(f"/api/projects/{_PROJECT_ID}/ui-automation/scripts/{_SCRIPT_ID}")
    assert resp.status_code == 200


def test_run_ui_test(monkeypatch) -> None:
    from app.schemas.ui_automation import UiTestRunDetail

    async def _fake_run(db, *, user, project_id, script_id):
        return UiTestRunDetail(
            id=str(_RUN_ID),
            scriptId=str(script_id),
            status="QUEUED",
            createdAt=1710000000,
            updatedAt=1710000000,
        )

    monkeypatch.setattr(ui_automation_endpoint, "run_ui_test", _fake_run)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/ui-automation/scripts/{_SCRIPT_ID}/run",
        json={},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["scriptId"] == str(_SCRIPT_ID)
    assert body["data"]["status"] == "QUEUED"
