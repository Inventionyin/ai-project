from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid


@dataclass(frozen=True)
class PluginSandboxResult:
    execution_id: str
    status: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool
    output: dict | None
    error: str | None
    sandbox_dir: str | None


def _safe_env() -> dict[str, str]:
    allowed_names = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "COMSPEC",
        "TEMP",
        "TMP",
        "PYTHONPATH",
        "PYTHONIOENCODING",
    }
    env = {name: value for name, value in os.environ.items() if name.upper() in allowed_names}
    env["PYTHONIOENCODING"] = "utf-8"
    for name in list(env):
        lowered = name.lower()
        if any(marker in lowered for marker in ("token", "secret", "password", "key")):
            env.pop(name, None)
    backend_root = str(Path(__file__).resolve().parents[2])
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = backend_root if not existing_pythonpath else f"{backend_root}{os.pathsep}{existing_pythonpath}"
    return env


async def run_plugin_sandbox(
    *,
    plugin_slug: str,
    entry_point: str,
    payload: dict | None,
    sandbox_policy: dict,
) -> PluginSandboxResult:
    execution_id = f"plug_{uuid.uuid4().hex}"
    timeout_seconds = max(float(sandbox_policy.get("timeoutMs", 30000)) / 1000.0, 0.1)
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix=f"weitesting-plugin-{plugin_slug}-") as sandbox_dir:
        request_payload = {
            "executionId": execution_id,
            "pluginSlug": plugin_slug,
            "payload": payload or {},
            "sandboxPolicy": sandbox_policy,
        }
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "app.services.plugin_sandbox_runner",
            entry_point,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Path(sandbox_dir)),
            env=_safe_env(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(json.dumps(request_payload, ensure_ascii=False).encode("utf-8")),
                timeout=timeout_seconds,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
        except TimeoutError:
            process.kill()
            await process.communicate()
            return PluginSandboxResult(
                execution_id=execution_id,
                status="timeout",
                exit_code=None,
                duration_ms=int((time.perf_counter() - started) * 1000),
                timed_out=True,
                output=None,
                error=f"Plugin execution exceeded sandboxPolicy.timeoutMs={sandbox_policy.get('timeoutMs')}",
                sandbox_dir=None,
            )

    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    stderr_text = stderr.decode("utf-8", errors="replace").strip()
    parsed: dict = {}
    if stdout_text:
        try:
            parsed = json.loads(stdout_text)
        except json.JSONDecodeError:
            parsed = {"ok": process.returncode == 0, "output": {"stdout": stdout_text}}

    ok = process.returncode == 0 and bool(parsed.get("ok", process.returncode == 0))
    return PluginSandboxResult(
        execution_id=execution_id,
        status="completed" if ok else "failed",
        exit_code=process.returncode,
        duration_ms=duration_ms,
        timed_out=False,
        output=parsed.get("output") if isinstance(parsed.get("output"), dict) else None,
        error=(parsed.get("error") or stderr_text or None) if not ok else None,
        sandbox_dir=None,
    )
