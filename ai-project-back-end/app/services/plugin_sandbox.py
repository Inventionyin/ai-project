from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
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


_SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?i)(access[_-]?token|token|secret|password|api[_-]?key|authorization|bearer)\s*[:=]\s*[^&\s,;]+"
)
_ALLOWED_PERMISSIONS = {"RUN_TEST", "READ_PROJECT", "WRITE_REPORT", "CALL_EXTERNAL"}
_ALLOWED_NETWORK_MODES = {"OFF", "ALLOWLIST"}
_SANDBOX_POLICY_KEYS = {"permissions", "timeoutMs", "networkMode", "allowedHosts", "maxPayloadBytes"}
_HOSTNAME_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*$")


def _redact_text(value: object) -> str:
    text = str(value or "")
    text = _SENSITIVE_TEXT_PATTERN.sub(lambda m: f"{m.group(1)}=***REDACTED***", text)
    return text[:1000]


def _safe_env(*, sandbox_dir: Path) -> dict[str, str]:
    allowed_names = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "COMSPEC",
        "PYTHONIOENCODING",
    }
    env = {name: value for name, value in os.environ.items() if name.upper() in allowed_names}
    env["PYTHONIOENCODING"] = "utf-8"
    local_tmp = sandbox_dir / "tmp"
    local_home = sandbox_dir / "home"
    local_tmp.mkdir(parents=True, exist_ok=True)
    local_home.mkdir(parents=True, exist_ok=True)
    env["TEMP"] = str(local_tmp)
    env["TMP"] = str(local_tmp)
    env["TMPDIR"] = str(local_tmp)
    env["HOME"] = str(local_home)
    env["USERPROFILE"] = str(local_home)
    for name in list(env):
        lowered = name.lower()
        if any(marker in lowered for marker in ("token", "secret", "password", "key")):
            env.pop(name, None)
    backend_root = str(Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = backend_root
    return env


def validate_sandbox_policy(policy: dict | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(policy, dict):
        return ["sandboxPolicy must be an object; migrate this plugin configuration before execution"]

    extra_keys = sorted(set(policy) - _SANDBOX_POLICY_KEYS)
    if extra_keys:
        errors.append(f"sandboxPolicy contains unsupported fields: {', '.join(extra_keys)}")

    permissions = policy.get("permissions")
    if not isinstance(permissions, list) or any(not isinstance(item, str) for item in permissions):
        errors.append("sandboxPolicy.permissions must be a string list")
    else:
        invalid = [item for item in permissions if item not in _ALLOWED_PERMISSIONS]
        if invalid:
            errors.append("sandboxPolicy.permissions contains invalid values")

    timeout_ms = policy.get("timeoutMs")
    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or not (100 <= timeout_ms <= 120000):
        errors.append("sandboxPolicy.timeoutMs must be an integer between 100 and 120000")

    network_mode = policy.get("networkMode")
    if network_mode not in _ALLOWED_NETWORK_MODES:
        errors.append("sandboxPolicy.networkMode must be OFF or ALLOWLIST")

    allowed_hosts = policy.get("allowedHosts")
    if not isinstance(allowed_hosts, list) or any(not isinstance(item, str) for item in allowed_hosts):
        errors.append("sandboxPolicy.allowedHosts must be a string list")
    elif network_mode == "OFF" and allowed_hosts:
        errors.append("sandboxPolicy.allowedHosts must be empty when networkMode=OFF")
    elif network_mode == "ALLOWLIST":
        if "CALL_EXTERNAL" not in (permissions if isinstance(permissions, list) else []):
            errors.append("sandboxPolicy.permissions must include CALL_EXTERNAL when networkMode=ALLOWLIST")
        if not allowed_hosts:
            errors.append("sandboxPolicy.allowedHosts required when networkMode=ALLOWLIST")
        elif any(not _HOSTNAME_RE.fullmatch(item) for item in allowed_hosts):
            errors.append("sandboxPolicy.allowedHosts contains invalid hostname")

    max_payload_bytes = policy.get("maxPayloadBytes")
    if isinstance(max_payload_bytes, bool) or not isinstance(max_payload_bytes, int) or not (1024 <= max_payload_bytes <= 1048576):
        errors.append("sandboxPolicy.maxPayloadBytes must be an integer between 1024 and 1048576")

    return errors


def _format_runner_error(error: object, stderr_text: str) -> str | None:
    if isinstance(error, dict):
        code = _redact_text(error.get("code") or "plugin_error")
        message = _redact_text(error.get("message") or "")
        details = error.get("details")
        if isinstance(details, list) and details:
            detail_text = "; ".join(_redact_text(item) for item in details[:5])
            return f"{code}: {message} ({detail_text})"
        return f"{code}: {message}".strip()
    if error:
        return _redact_text(error)
    if stderr_text:
        return _redact_text(stderr_text)
    return None


async def run_plugin_sandbox(
    *,
    plugin_slug: str,
    entry_point: str,
    payload: dict | None,
    sandbox_policy: dict,
) -> PluginSandboxResult:
    execution_id = f"plug_{uuid.uuid4().hex}"
    policy_errors = validate_sandbox_policy(sandbox_policy)
    if policy_errors:
        return PluginSandboxResult(
            execution_id=execution_id,
            status="failed",
            exit_code=None,
            duration_ms=0,
            timed_out=False,
            output=None,
            error=f"sandbox policy rejected: {'; '.join(policy_errors)}",
            sandbox_dir=None,
        )
    timeout_seconds = max(float(sandbox_policy.get("timeoutMs", 30000)) / 1000.0, 0.1)
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix=f"weitesting-plugin-{plugin_slug}-") as sandbox_dir:
        sandbox_path = Path(sandbox_dir)
        work_dir = sandbox_path / "work"
        work_dir.mkdir(parents=True, exist_ok=True)
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
            cwd=str(work_dir),
            env=_safe_env(sandbox_dir=sandbox_path),
            close_fds=True,
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
    error = _format_runner_error(parsed.get("error"), stderr_text) if not ok else None
    return PluginSandboxResult(
        execution_id=execution_id,
        status="completed" if ok else "failed",
        exit_code=process.returncode,
        duration_ms=duration_ms,
        timed_out=False,
        output=parsed.get("output") if isinstance(parsed.get("output"), dict) else None,
        error=error,
        sandbox_dir=None,
    )
