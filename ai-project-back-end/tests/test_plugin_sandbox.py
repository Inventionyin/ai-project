from __future__ import annotations

import asyncio
import json
from pathlib import Path
import tempfile

import pytest

from app.services.plugin_sandbox import run_plugin_sandbox


class _FakeProcess:
    def __init__(self, *, returncode: int, stdout: bytes, stderr: bytes) -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.killed = False

    async def communicate(self, _input: bytes | None = None):
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.killed = True


class _TempDir:
    def __init__(self, path: Path) -> None:
        self._path = path

    def __enter__(self) -> str:
        self._path.mkdir(parents=True, exist_ok=True)
        return str(self._path)

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.anyio
async def test_plugin_sandbox_runs_builtin_echo_in_isolated_process() -> None:
    result = await run_plugin_sandbox(
        plugin_slug="echo",
        entry_point="builtin.echo",
        payload={"hello": "world"},
        sandbox_policy={
            "permissions": ["RUN_TEST"],
            "timeoutMs": 1000,
            "networkMode": "OFF",
            "allowedHosts": [],
            "maxPayloadBytes": 4096,
        },
    )

    assert result.status == "completed"
    assert result.exit_code == 0
    assert result.output["payload"] == {"hello": "world"}
    assert result.output["leakedSecretEnv"] == []
    assert result.execution_id
    assert result.duration_ms >= 0


@pytest.mark.anyio
async def test_plugin_sandbox_uses_sandbox_local_workdir_and_strips_sensitive_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sandbox_root = tmp_path / "plugin-sandbox-root"
    captured: dict[str, object] = {}

    async def _fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeProcess(
            returncode=0,
            stdout=json.dumps({"ok": True, "output": {"payload": {"hello": "world"}}}).encode("utf-8"),
            stderr=b"",
        )

    monkeypatch.setenv("API_TOKEN", "secret-token")
    monkeypatch.setenv("PASSWORD", "secret-password")
    monkeypatch.setenv("PATH", "C:\\Windows\\System32")
    monkeypatch.setenv("TEMP", str(tmp_path / "temp"))
    monkeypatch.setenv("TMP", str(tmp_path / "tmp"))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", lambda prefix=None: _TempDir(sandbox_root))

    result = await run_plugin_sandbox(
        plugin_slug="echo",
        entry_point="builtin.echo",
        payload={"hello": "world"},
        sandbox_policy={
            "permissions": ["RUN_TEST"],
            "timeoutMs": 1000,
            "networkMode": "OFF",
            "allowedHosts": [],
            "maxPayloadBytes": 4096,
        },
    )

    kwargs = captured["kwargs"]
    env = kwargs["env"]
    assert result.status == "completed"
    assert kwargs["cwd"] == str(sandbox_root / "work")
    assert env["TEMP"] == str(sandbox_root / "tmp")
    assert env["TMP"] == str(sandbox_root / "tmp")
    assert env["TMPDIR"] == str(sandbox_root / "tmp")
    assert env["HOME"] == str(sandbox_root / "home")
    assert env["USERPROFILE"] == str(sandbox_root / "home")
    assert "API_TOKEN" not in env
    assert "PASSWORD" not in env
    assert kwargs["close_fds"] is True


@pytest.mark.anyio
async def test_plugin_sandbox_refuses_invalid_policy_without_spawning(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    async def _fake_create_subprocess_exec(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("sandbox should not spawn for invalid policy")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)

    result = await run_plugin_sandbox(
        plugin_slug="echo",
        entry_point="builtin.echo",
        payload={"hello": "world"},
        sandbox_policy={
            "permissions": ["RUN_TEST"],
            "timeoutMs": "1000",
            "networkMode": "OFF",
            "allowedHosts": [],
            "maxPayloadBytes": 4096,
        },
    )

    assert called is False
    assert result.status == "failed"
    assert result.exit_code is None
    assert result.error and "sandbox policy" in result.error.lower()


@pytest.mark.anyio
async def test_plugin_sandbox_reports_runner_errors_concisely(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_create_subprocess_exec(*args, **kwargs):
        return _FakeProcess(
            returncode=1,
            stdout=json.dumps({
                "ok": False,
                "error": {
                    "code": "policy_invalid",
                    "message": "Sandbox policy is invalid",
                    "details": ["sandboxPolicy.timeoutMs must be an integer"],
                },
            }).encode("utf-8"),
            stderr=b"stack trace with secret-token=super-secret-value",
        )

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)

    result = await run_plugin_sandbox(
        plugin_slug="echo",
        entry_point="builtin.echo",
        payload={"hello": "world"},
        sandbox_policy={
            "permissions": ["RUN_TEST"],
            "timeoutMs": 1000,
            "networkMode": "OFF",
            "allowedHosts": [],
            "maxPayloadBytes": 4096,
        },
    )

    assert result.status == "failed"
    assert isinstance(result.error, str)
    assert "policy_invalid" in result.error
    assert "super-secret-value" not in result.error


@pytest.mark.anyio
async def test_plugin_sandbox_rejects_external_call_when_network_is_off() -> None:
    result = await run_plugin_sandbox(
        plugin_slug="http",
        entry_point="builtin.http-get",
        payload={"url": "https://example.com/status"},
        sandbox_policy={
            "permissions": ["RUN_TEST", "CALL_EXTERNAL"],
            "timeoutMs": 1000,
            "networkMode": "OFF",
            "allowedHosts": [],
            "maxPayloadBytes": 4096,
        },
    )

    assert result.status == "failed"
    assert "networkMode=OFF" in result.error


@pytest.mark.anyio
async def test_plugin_sandbox_enforces_timeout() -> None:
    result = await run_plugin_sandbox(
        plugin_slug="sleep",
        entry_point="builtin.sleep",
        payload={"seconds": 2},
        sandbox_policy={
            "permissions": ["RUN_TEST"],
            "timeoutMs": 100,
            "networkMode": "OFF",
            "allowedHosts": [],
            "maxPayloadBytes": 4096,
        },
    )

    assert result.status == "timeout"
    assert result.timed_out is True
