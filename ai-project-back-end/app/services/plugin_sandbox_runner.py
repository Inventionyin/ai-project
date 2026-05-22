from __future__ import annotations

import json
import os
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.services.plugin_sandbox import validate_sandbox_policy


def _read_request() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _write_response(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    sys.stdout.flush()


def _error(code: str, message: str, details: list[str] | None = None) -> dict:
    return {"code": code, "message": message, "details": details or []}


def _validate_runtime_request(request: dict) -> dict:
    policy = request.get("sandboxPolicy") if isinstance(request.get("sandboxPolicy"), dict) else {}
    details = validate_sandbox_policy(policy)
    payload = request.get("payload") if isinstance(request.get("payload"), dict) else {}
    payload_size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    max_payload = policy.get("maxPayloadBytes") if isinstance(policy.get("maxPayloadBytes"), int) else 0
    if max_payload and payload_size > max_payload:
        details.append("payload exceeds sandboxPolicy.maxPayloadBytes")
    if details:
        raise RuntimeError(json.dumps(_error("policy_invalid", "Sandbox policy is invalid", details), ensure_ascii=False))
    return policy


def _run(entry_point: str, request: dict) -> dict:
    payload = request.get("payload") if isinstance(request.get("payload"), dict) else {}
    policy = _validate_runtime_request(request)
    network_mode = str(policy.get("networkMode") or "OFF")
    allowed_hosts = set(policy.get("allowedHosts") or [])

    if entry_point == "builtin.echo":
        leaked_env = sorted(name for name in os.environ if any(marker in name.lower() for marker in ("token", "secret", "password", "key")))
        return {"payload": payload, "networkMode": network_mode, "leakedSecretEnv": leaked_env}

    if entry_point == "builtin.sleep":
        time.sleep(float(payload.get("seconds") or 0))
        return {"slept": float(payload.get("seconds") or 0)}

    if entry_point == "builtin.http-get":
        url = str(payload.get("url") or "")
        host = urlparse(url).hostname or ""
        if network_mode == "OFF":
            raise RuntimeError("Outbound network is blocked by sandboxPolicy.networkMode=OFF")
        if "CALL_EXTERNAL" not in set(policy.get("permissions") or []):
            raise RuntimeError("CALL_EXTERNAL permission is required for builtin.http-get")
        if network_mode == "ALLOWLIST" and host not in allowed_hosts:
            raise RuntimeError(f"Host is not allowed by sandboxPolicy.allowedHosts: {host}")
        request_obj = Request(url, headers={"User-Agent": "WeiTesting-PluginSandbox/1.0"})
        with urlopen(request_obj, timeout=5) as response:  # noqa: S310 - explicit allowlist gate above
            return {"url": url, "statusCode": response.status, "bytes": len(response.read(1024))}

    raise RuntimeError(f"Unsupported plugin entry point: {entry_point}")


def main() -> int:
    try:
        entry_point = sys.argv[1]
        response = _run(entry_point, _read_request())
        _write_response({"ok": True, "output": response})
        return 0
    except Exception as exc:  # pragma: no cover - subprocess boundary
        text = str(exc)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and parsed.get("code"):
                _write_response({"ok": False, "error": parsed})
                return 1
        except json.JSONDecodeError:
            pass
        _write_response({"ok": False, "error": _error("runtime_error", text)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
