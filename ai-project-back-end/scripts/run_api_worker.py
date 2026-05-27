from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from app.models.enums import CaseRunStatus, JobStatus
from app.schemas.run import CaseRunMetrics, CaseRunResult
from app.schemas.worker import JobPayload
from app.services.runner_dispatch import dispatch_job_runner


@dataclass(slots=True)
class WorkerState:
    worker_id: str
    token: str


def _env(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    return value or default


def _required(value: str | None, *, field: str) -> str:
    if value is None or not str(value).strip():
        raise SystemExit(f"missing required setting: {field}")
    return str(value).strip()


def _parse_capabilities(raw: str | None) -> list[str]:
    if raw is None:
        return ["API"]
    values = [item.strip().upper() for item in raw.split(",") if item.strip()]
    return values or ["API"]


def _load_state(path: Path) -> WorkerState | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        worker_id = str(data.get("workerId") or "").strip()
        token = str(data.get("token") or "").strip()
    except Exception:
        return None
    if not worker_id or not token:
        return None
    return WorkerState(worker_id=worker_id, token=token)


def _save_state(path: Path, state: WorkerState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"workerId": state.worker_id, "token": state.token}, ensure_ascii=False, indent=2), encoding="utf-8")


class WorkerClient:
    def __init__(
        self,
        *,
        api_base_url: str,
        tenant_id: str,
        worker_name: str,
        capabilities: list[str],
        slots: int,
        version: str,
        state_path: Path,
        session: requests.Session | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.worker_name = worker_name
        self.capabilities = capabilities
        self.slots = slots
        self.version = version
        self.state_path = state_path
        self.session = session or requests.Session()
        self.state: WorkerState | None = _load_state(state_path)

    def _worker_headers(self) -> dict[str, str]:
        if self.state is None:
            raise RuntimeError("worker is not registered")
        return {"Authorization": f"Bearer {self.state.token}"}

    def _post(self, path: str, *, headers: dict[str, str] | None = None, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.post(
            f"{self.api_base_url}{path}",
            headers=headers,
            json=json_body,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        code = payload.get("code", -1)
        if int(code) != 0:
            raise RuntimeError(f"api_error:{path}:{payload.get('message')}")
        return dict(payload.get("data") or {})

    def ensure_registered(self) -> WorkerState:
        if self.state is not None:
            try:
                self._post(
                    "/api/workers/heartbeat",
                    headers=self._worker_headers(),
                    json_body={
                        "workerId": self.state.worker_id,
                        "slotsFree": self.slots,
                        "runningJobIds": [],
                        "meta": {},
                    },
                )
                return self.state
            except Exception:
                self.state = None

        data = self._post(
            "/api/workers/register",
            headers={"X-Tenant-Id": self.tenant_id},
            json_body={
                "name": self.worker_name,
                "capabilities": self.capabilities,
                "slots": self.slots,
                "version": self.version,
            },
        )
        self.state = WorkerState(worker_id=str(data["workerId"]), token=str(data["token"]))
        _save_state(self.state_path, self.state)
        return self.state

    def heartbeat(self, *, running_job_ids: list[str]) -> None:
        if self.state is None:
            self.ensure_registered()
        state = self.state
        if state is None:
            raise RuntimeError("worker is not registered")
        self._post(
            "/api/workers/heartbeat",
            headers=self._worker_headers(),
            json_body={
                "workerId": state.worker_id,
                "slotsFree": self.slots - len(running_job_ids),
                "runningJobIds": running_job_ids,
                "meta": {},
            },
        )

    def poll(self) -> tuple[JobPayload | None, int]:
        state = self.ensure_registered()
        data = self._post(
            "/api/workers/poll",
            headers=self._worker_headers(),
            json_body={"workerId": state.worker_id, "capabilities": self.capabilities},
        )
        job_raw = data.get("job")
        sleep_ms = int(data.get("sleepMs") or 2000)
        if not isinstance(job_raw, dict):
            return None, sleep_ms
        return JobPayload.model_validate(job_raw), sleep_ms

    def report(self, *, job: JobPayload, job_status: JobStatus, results: list[CaseRunResult]) -> None:
        if self.state is None:
            self.ensure_registered()
        state = self.state
        if state is None:
            raise RuntimeError("worker is not registered")
        self._post(
            "/api/workers/report",
            headers=self._worker_headers(),
            json_body={
                "workerId": state.worker_id,
                "jobId": job.jobId,
                "runId": job.runId,
                "jobStatus": job_status.value,
                "results": [result.model_dump(mode="json") for result in results],
            },
        )


def _failure_results(job: JobPayload, *, error_type: str, error_message: str) -> list[CaseRunResult]:
    now = int(time.time())
    return [
        CaseRunResult(
            caseRunId=item.caseRunId,
            status=CaseRunStatus.FAILED,
            startAt=now,
            endAt=now,
            errorType=error_type,
            errorMessage=error_message[:2000],
            logs=[error_message[:500]],
            artifacts=[],
            metrics=CaseRunMetrics(durationMs=0),
        )
        for item in job.items
    ]


def _execute_job(job: JobPayload) -> tuple[JobStatus, list[CaseRunResult]]:
    dispatched = dispatch_job_runner(job)
    if not dispatched.handled or dispatched.output is None:
        return JobStatus.FAILED, _failure_results(job, error_type="RUNNER_NOT_SUPPORTED", error_message=f"runner not supported: {job.execution.runnerType}")
    return dispatched.output.job_status, list(dispatched.output.results)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WeiTesting API worker")
    parser.add_argument("--api-base-url", default=_env("WEITESTING_WORKER_API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--tenant-id", default=_env("WEITESTING_WORKER_TENANT_ID"))
    parser.add_argument("--worker-name", default=_env("WEITESTING_WORKER_NAME", "weitesting-api-worker"))
    parser.add_argument("--capabilities", default=_env("WEITESTING_WORKER_CAPABILITIES", "API"))
    parser.add_argument("--slots", type=int, default=int(_env("WEITESTING_WORKER_SLOTS", "1") or "1"))
    parser.add_argument("--version", default=_env("WEITESTING_WORKER_VERSION", "1.0.0"))
    parser.add_argument("--state-path", default=_env("WEITESTING_WORKER_STATE_PATH", "var/worker-state.json"))
    parser.add_argument("--idle-sleep-ms", type=int, default=int(_env("WEITESTING_WORKER_IDLE_SLEEP_MS", "2000") or "2000"))
    parser.add_argument("--once", action="store_true", help="Poll once and exit after handling at most one job")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    tenant_id = _required(args.tenant_id, field="WEITESTING_WORKER_TENANT_ID")
    client = WorkerClient(
        api_base_url=str(args.api_base_url),
        tenant_id=tenant_id,
        worker_name=str(args.worker_name),
        capabilities=_parse_capabilities(args.capabilities),
        slots=max(1, int(args.slots)),
        version=str(args.version),
        state_path=Path(str(args.state_path)),
    )

    while True:
        client.ensure_registered()
        client.heartbeat(running_job_ids=[])
        job, sleep_ms = client.poll()
        if job is None:
            if args.once:
                return 0
            time.sleep(max(0.2, max(args.idle_sleep_ms, sleep_ms) / 1000))
            continue
        job_status, results = _execute_job(job)
        client.report(job=job, job_status=job_status, results=results)
        if args.once:
            return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as exc:
        body = ""
        if exc.response is not None:
            try:
                body = exc.response.text[:2000]
            except Exception:
                body = ""
        print(f"HTTP error: {exc} {body}".strip(), file=sys.stderr)
        raise
