from __future__ import annotations

import pytest

from app.services.plugin_sandbox import run_plugin_sandbox


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
    assert result.execution_id
    assert result.duration_ms >= 0


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
