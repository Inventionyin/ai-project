from __future__ import annotations

import json
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def _read_request() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _write_response(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    sys.stdout.flush()


def _run(entry_point: str, request: dict) -> dict:
    payload = request.get("payload") if isinstance(request.get("payload"), dict) else {}
    policy = request.get("sandboxPolicy") if isinstance(request.get("sandboxPolicy"), dict) else {}
    network_mode = str(policy.get("networkMode") or "OFF")
    allowed_hosts = set(policy.get("allowedHosts") or [])

    if entry_point == "builtin.echo":
        return {"payload": payload, "networkMode": network_mode}

    if entry_point == "builtin.sleep":
        time.sleep(float(payload.get("seconds") or 0))
        return {"slept": float(payload.get("seconds") or 0)}

    if entry_point == "builtin.http-get":
        url = str(payload.get("url") or "")
        host = urlparse(url).hostname or ""
        if network_mode == "OFF":
            raise RuntimeError("Outbound network is blocked by sandboxPolicy.networkMode=OFF")
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
        _write_response({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
