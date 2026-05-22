from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import plugins as plugins_endpoint
from app.core.database import get_db
from app.models.enums import PluginInstallStatus, PluginStatus
from app.models.plugin import Plugin, PluginInstallation


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app(include_project_router: bool = False) -> FastAPI:
    app = FastAPI()
    app.include_router(plugins_endpoint.router, prefix="/api")
    if include_project_router:
        app.include_router(plugins_endpoint.project_router, prefix="/api")

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_create_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_create(db, *, user, name, slug, version, **kwargs):
        from app.schemas.plugin import PluginDetail
        return PluginDetail(
            id="33333333-3333-3333-3333-333333333333",
            name=name,
            slug=slug,
            version=version,
            pluginType="executor",
            enabled=True,
            status="AVAILABLE",
            downloadCount=0,
            createdAt=1700000000,
            updatedAt=1700000000,
            sandboxPolicy={
                "permissions": ["RUN_TEST"],
                "timeoutMs": 1000,
                "networkMode": "OFF",
                "allowedHosts": [],
                "maxPayloadBytes": 4096,
            },
        )

    monkeypatch.setattr(plugins_endpoint, "create_plugin", _fake_create)
    app = _build_app()
    client = TestClient(app)
    resp = client.post(
        "/api/plugins",
        json={"name": "JMeter Plugin", "slug": "jmeter", "version": "1.0.0"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["slug"] == "jmeter"


@pytest.mark.anyio
async def test_create_plugin_rejects_loose_sandbox_policy_shape() -> None:
    from app.services.plugin import create_plugin

    class _CreateSession:
        async def scalar(self, _stmt):
            return None

        def add(self, _row):
            return None

        async def flush(self):
            return None

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )

    with pytest.raises(HTTPException) as exc:
        await create_plugin(
            _CreateSession(),
            user=user,
            name="bad-policy",
            slug="bad-policy",
            version="1.0.0",
            config_schema={"sandboxPolicy": {"permissions": "RUN_TEST", "timeoutMs": 1000, "networkMode": "OFF", "allowedHosts": [], "maxPayloadBytes": 4096}},
        )

    assert exc.value.status_code == 400
    assert "string list" in str(exc.value.detail)


def test_list_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_list(db, *, user, page, page_size):
        return 0, []

    monkeypatch.setattr(plugins_endpoint, "list_plugins", _fake_list)
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/api/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 0


def test_install_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    plugin_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_install(db, *, user, project_id, plugin_id, config=None):
        from app.schemas.plugin import PluginInstallationDetail
        return PluginInstallationDetail(
            id="44444444-4444-4444-4444-444444444444",
            projectId=str(project_id),
            pluginId=str(plugin_id),
            pluginName="JMeter Plugin",
            pluginSlug="jmeter",
            status="INSTALLED",
            installedVersion="1.0.0",
            createdAt=1700000000,
            updatedAt=1700000000,
            sandboxPolicy={
                "permissions": ["RUN_TEST"],
                "timeoutMs": 1000,
                "networkMode": "OFF",
                "allowedHosts": [],
                "maxPayloadBytes": 4096,
            },
        )

    monkeypatch.setattr(plugins_endpoint, "install_plugin", _fake_install)
    app = _build_app(include_project_router=True)
    client = TestClient(app)
    resp = client.post(
        f"/api/projects/{project_id}/plugins/install",
        json={"pluginId": str(plugin_id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "INSTALLED"


def test_invoke_plugin_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    installation_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    async def _fake_invoke(db, *, user, project_id, installation_id, payload=None):
        from app.services.plugin import PluginInvokeResponse

        return PluginInvokeResponse(
            installationId=str(installation_id),
            pluginId="33333333-3333-3333-3333-333333333333",
            pluginSlug="jmeter",
            status="accepted",
            sandboxPolicy={
                "permissions": ["RUN_TEST"],
                "timeoutMs": 1000,
                "networkMode": "OFF",
                "allowedHosts": [],
                "maxPayloadBytes": 4096,
            },
        )

    monkeypatch.setattr(plugins_endpoint, "invoke_plugin_installation", _fake_invoke)
    app = _build_app(include_project_router=True)
    client = TestClient(app)
    resp = client.post(f"/api/projects/{project_id}/plugins/installations/{installation_id}/invoke")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert {"installationId", "pluginId", "pluginSlug", "status", "sandboxPolicy"}.issubset(set(data["data"].keys()))
    assert {"executionId", "exitCode", "durationMs", "timedOut", "output", "error"}.issubset(set(data["data"].keys()))
    assert data["data"]["status"] == "accepted"
    assert data["data"]["pluginSlug"] == "jmeter"


def test_invoke_plugin_endpoint_missing_installation(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    installation_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    async def _fake_invoke(db, *, user, project_id, installation_id, payload=None):
        raise HTTPException(status_code=404, detail="Installation not found")

    monkeypatch.setattr(plugins_endpoint, "invoke_plugin_installation", _fake_invoke)
    app = _build_app(include_project_router=True)
    client = TestClient(app)
    resp = client.post(f"/api/projects/{project_id}/plugins/installations/{installation_id}/invoke")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Installation not found"


def test_list_plugin_invocations(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    installation_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    async def _fake_list(db, *, user, project_id, installation_id, page, page_size):
        from app.schemas.plugin import PluginInvokeRecordDetail
        return 1, [
            PluginInvokeRecordDetail(
                id="55555555-5555-5555-5555-555555555555",
                installationId=str(installation_id),
                pluginId="33333333-3333-3333-3333-333333333333",
                pluginSlug="jmeter",
                invokedBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                status="accepted",
                createdAt=1700000000,
            )
        ]

    monkeypatch.setattr(plugins_endpoint, "list_plugin_invocations", _fake_list)
    app = _build_app(include_project_router=True)
    client = TestClient(app)
    resp = client.get(f"/api/projects/{project_id}/plugins/installations/{installation_id}/invocations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["status"] == "accepted"


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class _PluginResolveSession:
    def __init__(self, row):
        self._row = row

    async def scalar(self, _stmt):
        from app.models.project import Project
        project = Project(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            name="P1",
            owner_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        )
        return project

    async def execute(self, _stmt):
        return _ScalarResult(self._row)


def _plugin_installation_pair(*, plugin_enabled: bool = True, install_status: str = "INSTALLED"):
    plugin_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    plugin = Plugin(
        id=plugin_id,
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        name="JMeter Plugin",
        slug="jmeter",
        version="1.0.0",
        plugin_type="executor",
        enabled=plugin_enabled,
        status=PluginStatus.AVAILABLE.value,
        download_count=0,
    )
    installation = PluginInstallation(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        plugin_id=plugin_id,
        status=install_status,
        installed_version="1.0.0",
    )
    return installation, plugin


class _InvokeSession:
    def __init__(self, installation: PluginInstallation, resolve_row):
        self._installation = installation
        self._resolve_row = resolve_row
        self.audit_rows = []

    async def scalar(self, stmt):
        from app.models.project import Project

        stmt_text = str(stmt)
        if "plugin_installations" in stmt_text:
            return self._installation
        return Project(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            name="P1",
            owner_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        )

    async def execute(self, _stmt):
        return _ScalarResult(self._resolve_row)

    def add(self, row):
        self.audit_rows.append(row)

    async def flush(self):
        return None


@pytest.mark.anyio
async def test_resolve_enabled_plugin_installation_allows_enabled_plugin() -> None:
    from app.services.plugin import resolve_enabled_plugin_installation

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    installation, plugin = await resolve_enabled_plugin_installation(
        _PluginResolveSession(_plugin_installation_pair()),
        user=user,
        project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        plugin_slug="jmeter",
    )

    assert installation.status == PluginInstallStatus.INSTALLED.value
    assert plugin.slug == "jmeter"


@pytest.mark.anyio
async def test_resolve_enabled_plugin_installation_rejects_disabled_plugin() -> None:
    from app.services.plugin import resolve_enabled_plugin_installation

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )

    with pytest.raises(HTTPException) as exc:
        await resolve_enabled_plugin_installation(
            _PluginResolveSession(_plugin_installation_pair(plugin_enabled=False)),
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            plugin_slug="jmeter",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Plugin is disabled"


@pytest.mark.anyio
async def test_resolve_enabled_plugin_installation_rejects_uninstalled_plugin() -> None:
    from app.services.plugin import resolve_enabled_plugin_installation

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )

    with pytest.raises(HTTPException) as exc:
        await resolve_enabled_plugin_installation(
            _PluginResolveSession(_plugin_installation_pair(install_status=PluginInstallStatus.UNINSTALLED.value)),
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            plugin_slug="jmeter",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Plugin is uninstalled"


@pytest.mark.anyio
async def test_invoke_plugin_installation_allows_ready_callable() -> None:
    from app.services.plugin import invoke_plugin_installation

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    installation, plugin = _plugin_installation_pair()
    session = _InvokeSession(installation, (installation, plugin))
    result = await invoke_plugin_installation(
        session,
        user=user,
        project_id=installation.project_id,
        installation_id=installation.id,
    )
    assert result.status == "accepted"
    assert result.pluginSlug == "jmeter"
    assert result.sandboxPolicy.networkMode == "OFF"
    assert session.audit_rows
    assert session.audit_rows[0].detail_json["sandbox_policy"]["networkMode"] == "OFF"


@pytest.mark.anyio
async def test_invoke_plugin_installation_records_sandbox_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import plugin as plugin_service
    from app.services.plugin import invoke_plugin_installation
    from app.services.plugin_sandbox import PluginSandboxResult

    async def _fake_sandbox(*, plugin_slug, entry_point, payload, sandbox_policy):
        return PluginSandboxResult(
            execution_id="exec_123",
            status="completed",
            exit_code=0,
            duration_ms=12,
            timed_out=False,
            output={"ok": True},
            error=None,
            sandbox_dir=None,
        )

    monkeypatch.setattr(plugin_service, "run_plugin_sandbox", _fake_sandbox)
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    installation, plugin = _plugin_installation_pair()
    plugin.entry_point = "builtin.echo"
    session = _InvokeSession(installation, (installation, plugin))

    result = await invoke_plugin_installation(
        session,
        user=user,
        project_id=installation.project_id,
        installation_id=installation.id,
        payload={"ping": "pong"},
    )

    assert result.status == "completed"
    assert result.executionId == "exec_123"
    assert result.durationMs == 12
    assert session.audit_rows[0].detail_json["execution"]["status"] == "completed"


@pytest.mark.anyio
async def test_invoke_plugin_installation_rejects_legacy_loose_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.plugin import invoke_plugin_installation

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    installation, plugin = _plugin_installation_pair()
    installation.config_json = {
        "sandboxPolicy": {
            "permissions": ["RUN_TEST"],
            "timeoutMs": "1000",
            "networkMode": "OFF",
            "allowedHosts": [],
            "maxPayloadBytes": 4096,
            "legacy": True,
        }
    }
    session = _InvokeSession(installation, (installation, plugin))

    with pytest.raises(HTTPException) as exc:
        await invoke_plugin_installation(
            session,
            user=user,
            project_id=installation.project_id,
            installation_id=installation.id,
        )

    assert exc.value.status_code == 400
    assert "legacy" in str(exc.value.detail).lower() or "sandboxpolicy" in str(exc.value.detail).lower()
    assert not session.audit_rows


@pytest.mark.anyio
async def test_create_plugin_rejects_invalid_sandbox_policy_permissions() -> None:
    from app.services.plugin import create_plugin

    class _CreateSession:
        async def scalar(self, _stmt):
            return None

        def add(self, _row):
            return None

        async def flush(self):
            return None

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    with pytest.raises(HTTPException) as exc:
        await create_plugin(
            _CreateSession(),
            user=user,
            name="bad",
            slug="bad",
            version="1.0.0",
            config_schema={"sandboxPolicy": {"permissions": ["ROOT"], "timeoutMs": 1000, "networkMode": "OFF", "allowedHosts": [], "maxPayloadBytes": 4096}},
        )
    assert exc.value.status_code == 400
    assert "permissions" in str(exc.value.detail)


@pytest.mark.anyio
async def test_create_plugin_accepts_allowlist_sandbox_hosts_with_external_permission() -> None:
    from app.services.plugin import invoke_plugin_installation

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    installation, plugin = _plugin_installation_pair()
    installation.config_json = {
        "sandboxPolicy": {
            "permissions": ["RUN_TEST", "CALL_EXTERNAL"],
            "timeoutMs": 1000,
            "networkMode": "ALLOWLIST",
            "allowedHosts": ["api.example.com", "internal-service"],
            "maxPayloadBytes": 4096,
        }
    }

    result = await invoke_plugin_installation(
        _InvokeSession(installation, (installation, plugin)),
        user=user,
        project_id=installation.project_id,
        installation_id=installation.id,
    )

    assert result.sandboxPolicy.networkMode == "ALLOWLIST"
    assert result.sandboxPolicy.allowedHosts == ["api.example.com", "internal-service"]


def test_installation_detail_exposes_legacy_policy_diagnostics() -> None:
    from app.services.plugin import _to_install_detail

    installation, plugin = _plugin_installation_pair()
    now = datetime.now(timezone.utc)
    installation.created_at = now
    installation.updated_at = now
    installation.config_json = {
        "sandboxPolicy": {
            "permissions": ["RUN_TEST"],
            "timeoutMs": "1000",
            "networkMode": "OFF",
            "allowedHosts": [],
            "maxPayloadBytes": 4096,
            "legacy": True,
        }
    }

    detail = _to_install_detail(installation, plugin)

    assert detail.sandboxPolicy.networkMode == "OFF"
    assert detail.sandboxPolicyValid is False
    assert detail.sandboxPolicyError
    assert "migrate" in detail.sandboxPolicyError.lower()


def test_plugin_detail_exposes_non_object_policy_diagnostics() -> None:
    from app.services.plugin import _to_plugin_detail

    _, plugin = _plugin_installation_pair()
    now = datetime.now(timezone.utc)
    plugin.created_at = now
    plugin.updated_at = now
    plugin.config_schema_json = {"sandboxPolicy": "legacy"}

    detail = _to_plugin_detail(plugin)

    assert detail.sandboxPolicyValid is False
    assert detail.sandboxPolicyError
    assert "migrate" in detail.sandboxPolicyError.lower()


@pytest.mark.anyio
async def test_create_plugin_rejects_allowlist_sandbox_without_hosts() -> None:
    from app.services.plugin import create_plugin

    class _CreateSession:
        async def scalar(self, _stmt):
            return None

        def add(self, _row):
            return None

        async def flush(self):
            return None

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )

    with pytest.raises(HTTPException) as exc:
        await create_plugin(
            _CreateSession(),
            user=user,
            name="allowlist",
            slug="allowlist",
            version="1.0.0",
            config_schema={
                "sandboxPolicy": {
                    "permissions": ["RUN_TEST"],
                    "timeoutMs": 1000,
                    "networkMode": "ALLOWLIST",
                    "allowedHosts": [],
                    "maxPayloadBytes": 4096,
                }
            },
        )

    assert exc.value.status_code == 400
    assert "allowedHosts required" in str(exc.value.detail)


@pytest.mark.anyio
async def test_create_plugin_rejects_allowlist_sandbox_invalid_hosts() -> None:
    from app.services.plugin import create_plugin

    class _CreateSession:
        async def scalar(self, _stmt):
            return None

        def add(self, _row):
            return None

        async def flush(self):
            return None

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )

    with pytest.raises(HTTPException) as exc:
        await create_plugin(
            _CreateSession(),
            user=user,
            name="bad-host",
            slug="bad-host",
            version="1.0.0",
            config_schema={
                "sandboxPolicy": {
                    "permissions": ["RUN_TEST"],
                    "timeoutMs": 1000,
                    "networkMode": "ALLOWLIST",
                    "allowedHosts": ["https://api.example.com", "bad host"],
                    "maxPayloadBytes": 4096,
                }
            },
        )

    assert exc.value.status_code == 400
    assert "invalid hostname" in str(exc.value.detail)


@pytest.mark.anyio
async def test_invoke_plugin_installation_rejects_disabled_plugin() -> None:
    from app.services.plugin import invoke_plugin_installation

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    installation, plugin = _plugin_installation_pair(plugin_enabled=False)
    with pytest.raises(HTTPException) as exc:
        await invoke_plugin_installation(
            _InvokeSession(installation, (installation, plugin)),
            user=user,
            project_id=installation.project_id,
            installation_id=installation.id,
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "Plugin is disabled"


@pytest.mark.anyio
async def test_invoke_plugin_installation_rejects_non_callable_plugin_status() -> None:
    from app.services.plugin import invoke_plugin_installation

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    installation, plugin = _plugin_installation_pair()
    plugin.status = PluginStatus.DISABLED.value
    with pytest.raises(HTTPException) as exc:
        await invoke_plugin_installation(
            _InvokeSession(installation, (installation, plugin)),
            user=user,
            project_id=installation.project_id,
            installation_id=installation.id,
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == f"Plugin status is not callable: {PluginStatus.DISABLED.value}"


@pytest.mark.anyio
async def test_invoke_plugin_installation_rejects_payload_too_large() -> None:
    from app.services.plugin import invoke_plugin_installation

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    installation, plugin = _plugin_installation_pair()
    installation.config_json = {
        "sandboxPolicy": {
            "permissions": ["RUN_TEST"],
            "timeoutMs": 1000,
            "networkMode": "OFF",
            "allowedHosts": [],
            "maxPayloadBytes": 1024,
        }
    }
    with pytest.raises(HTTPException) as exc:
        await invoke_plugin_installation(
            _InvokeSession(installation, (installation, plugin)),
            user=user,
            project_id=installation.project_id,
            installation_id=installation.id,
            payload={"blob": "x" * 2000},
        )
    assert exc.value.status_code == 400
    assert "maxPayloadBytes" in str(exc.value.detail)
