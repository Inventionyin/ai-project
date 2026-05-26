from __future__ import annotations

import json
import platform
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from app.core.config import get_settings
from app.models.enums import ArtifactType, CaseRunStatus, JobStatus
from app.schemas.run import ArtifactIndex, CaseRunMetrics, CaseRunResult
from app.schemas.worker import JobItem, JobPayload
from app.services.runner_pytest_allure import _order_job_items


@dataclass(frozen=True, slots=True)
class NewmanExecutionOutput:
    job_status: JobStatus
    results: list[CaseRunResult]
    workspace: Path


def _default_runner_root() -> Path:
    settings = get_settings()
    configured = str(settings.runner_workspace_root or "").strip()
    if configured:
        return Path(configured).expanduser()
    if platform.system().strip().lower().startswith("win"):
        return Path("D:/ai-test-platform-runners")
    return Path(tempfile.gettempdir()) / "ai-test-platform-runners"


def _case_key(item: JobItem) -> str:
    return str(item.testCaseId or item.testcaseId or item.caseRunId).strip() or str(item.caseRunId)


def _normalize_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def _merge_url(base_url: str, api_url: str, params: dict[str, object]) -> str:
    raw = str(api_url or "").strip()
    if raw.startswith(("http://", "https://", "{{")):
        merged = raw
    else:
        base = str(base_url or "").rstrip("/")
        suffix = raw if raw.startswith("/") else f"/{raw}"
        merged = f"{{{{baseUrl}}}}{suffix}" if base else suffix
    query = urlencode({str(k): _normalize_value(v) for k, v in params.items() if v is not None})
    if not query:
        return merged
    joiner = "&" if "?" in merged else "?"
    return f"{merged}{joiner}{query}"


def _build_test_script(item: JobItem) -> list[str]:
    lines: list[str] = []
    if item.expectedStatusCode is not None:
        lines.extend(
            [
                f"pm.test('status code {int(item.expectedStatusCode)}', function () {{",
                f"  pm.response.to.have.status({int(item.expectedStatusCode)});",
                "});",
            ]
        )
    expected = str(item.expectedResult or "").strip()
    if expected:
        lines.extend(
            [
                "pm.test('response contains expected text', function () {",
                f"  pm.expect(pm.response.text()).to.include({json.dumps(expected, ensure_ascii=False)});",
                "});",
            ]
        )
    return lines


def _build_collection(job: JobPayload, ordered_items: list[JobItem]) -> dict[str, object]:
    collection_items: list[dict[str, object]] = []
    for item in ordered_items:
        headers = [
            {"key": str(key), "value": str(value)}
            for key, value in dict(item.headers or {}).items()
            if str(key).strip()
        ]
        request: dict[str, object] = {
            "method": str(item.apiMethod or "GET").strip().upper() or "GET",
            "header": headers,
            "url": {"raw": _merge_url(str(job.env.baseUrl), str(item.apiUrl or ""), dict(item.params or {}))},
        }
        events = []
        script_lines = _build_test_script(item)
        if script_lines:
            events.append({"listen": "test", "script": {"type": "text/javascript", "exec": script_lines}})
        collection_items.append(
            {
                "name": _case_key(item),
                "request": request,
                "event": events,
            }
        )
    return {
        "info": {
            "name": f"WeiTesting Run {job.runId}",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": collection_items,
    }


def _build_environment(job: JobPayload, ordered_items: list[JobItem]) -> dict[str, object]:
    values: dict[str, str] = {"baseUrl": str(job.env.baseUrl).rstrip("/")}
    values.update({str(k): str(v) for k, v in dict(job.env.variables or {}).items()})
    values.update({str(k): str(v) for k, v in dict(job.env.secrets or {}).items()})
    for item in ordered_items:
        for key, value in dict(item.params or {}).items():
            values.setdefault(str(key), _normalize_value(value))
    return {
        "name": f"WeiTesting Env {job.runId}",
        "values": [{"key": key, "value": value, "type": "default", "enabled": True} for key, value in values.items()],
    }


def _artifact(path: Path, *, kind: str) -> ArtifactIndex | None:
    if not path.exists():
        return None
    return ArtifactIndex(
        type=ArtifactType.LOG_BUNDLE,
        storageKey=str(path),
        meta={"name": path.name, "kind": kind, "size": path.stat().st_size},
    )


def _response_code(execution: dict[str, object]) -> int | None:
    response = execution.get("response")
    if not isinstance(response, dict):
        return None
    raw = response.get("code")
    try:
        return int(raw)  # type: ignore[arg-type]
    except Exception:
        return None


def _response_time_ms(execution: dict[str, object]) -> int:
    response = execution.get("response")
    if not isinstance(response, dict):
        return 0
    for key in ("responseTime", "response_time", "time"):
        raw = response.get(key)
        try:
            value = int(raw)  # type: ignore[arg-type]
        except Exception:
            continue
        return max(value, 0)
    return 0


def _assertion_error(execution: dict[str, object]) -> str:
    assertions = execution.get("assertions")
    if not isinstance(assertions, list):
        return ""
    messages: list[str] = []
    for assertion in assertions:
        if not isinstance(assertion, dict):
            continue
        error = assertion.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or "").strip()
        else:
            message = str(error or "").strip()
        name = str(assertion.get("assertion") or "").strip()
        combined = ": ".join([part for part in [name, message] if part]).strip()
        if combined:
            messages.append(combined)
    return "\n".join(messages)[:2000]


class NewmanRunnerService:
    def __init__(self, *, workspace_root: Path | None = None, newman_command: str = "newman") -> None:
        self._workspace_root = workspace_root
        self._newman_command = newman_command

    def execute(self, job: JobPayload) -> NewmanExecutionOutput:
        workspace = self._prepare_workspace(job)
        ordered_items = list(_order_job_items(job.items))
        collection_path = workspace / "collection.json"
        environment_path = workspace / "environment.json"
        report_path = workspace / "newman-report.json"
        execution_log = workspace / "execution.log"
        collection_path.write_text(json.dumps(_build_collection(job, ordered_items), ensure_ascii=False, indent=2), encoding="utf-8")
        environment_path.write_text(json.dumps(_build_environment(job, ordered_items), ensure_ascii=False, indent=2), encoding="utf-8")

        cmd = [
            self._newman_command,
            "run",
            str(collection_path),
            "-e",
            str(environment_path),
            "--reporters",
            "cli,json",
            "--reporter-json-export",
            str(report_path),
        ]
        start_ts = int(time.time())
        cli_error_type = ""
        cli_error_message = ""
        try:
            completed = subprocess.run(
                cmd,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=max(int(job.suiteConfig.timeoutSec), 1) * max(len(ordered_items), 1),
                check=False,
            )
        except FileNotFoundError:
            completed = subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr=f"{self._newman_command} not found")
            cli_error_type = "NEWMAN_NOT_FOUND"
            cli_error_message = f"{self._newman_command} not found; install it with npm install -g newman"
        except subprocess.TimeoutExpired as exc:
            completed = subprocess.CompletedProcess(args=cmd, returncode=1, stdout=str(exc.stdout or ""), stderr=str(exc.stderr or ""))
            cli_error_type = "NEWMAN_TIMEOUT"
            cli_error_message = "newman execution timeout"
        end_ts = int(time.time())

        execution_log.write_text(
            "\n".join(
                [
                    f"$ {' '.join(cmd)}",
                    f"returnCode={int(completed.returncode)}",
                    "--- stdout ---",
                    str(completed.stdout or ""),
                    "--- stderr ---",
                    str(completed.stderr or ""),
                ]
            ),
            encoding="utf-8",
        )
        artifacts = [item for item in [_artifact(execution_log, kind="EXECUTION_LOG"), _artifact(report_path, kind="NEWMAN_REPORT")] if item]
        executions = self._load_executions(report_path)
        results = self._build_case_results(
            ordered_items=ordered_items,
            executions=executions,
            artifacts=artifacts,
            fallback_start_ts=start_ts,
            fallback_end_ts=end_ts,
            cli_error_type=cli_error_type,
            cli_error_message=cli_error_message,
        )
        if any(result.status == CaseRunStatus.FAILED for result in results):
            job_status = JobStatus.FAILED
        elif int(completed.returncode) != 0 and not executions:
            job_status = JobStatus.FAILED
        else:
            job_status = JobStatus.DONE
        return NewmanExecutionOutput(job_status=job_status, results=results, workspace=workspace)

    def _prepare_workspace(self, job: JobPayload) -> Path:
        root = self._workspace_root or (_default_runner_root() / "newman")
        root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=f"job-{job.jobId}-", dir=root))

    def _load_executions(self, report_path: Path) -> list[dict[str, object]]:
        if not report_path.exists():
            return []
        try:
            raw = json.loads(report_path.read_text(encoding="utf-8") or "{}")
        except Exception:
            return []
        run = raw.get("run") if isinstance(raw, dict) else None
        executions = run.get("executions") if isinstance(run, dict) else None
        if not isinstance(executions, list):
            return []
        return [item for item in executions if isinstance(item, dict)]

    def _build_case_results(
        self,
        *,
        ordered_items: list[JobItem],
        executions: list[dict[str, object]],
        artifacts: list[ArtifactIndex],
        fallback_start_ts: int,
        fallback_end_ts: int,
        cli_error_type: str,
        cli_error_message: str,
    ) -> list[CaseRunResult]:
        results: list[CaseRunResult] = []
        for index, item in enumerate(ordered_items):
            execution = executions[index] if index < len(executions) else {}
            assertion_error = _assertion_error(execution)
            response_code = _response_code(execution)
            error_type: str | None = None
            error_message: str | None = None
            status = CaseRunStatus.PASSED
            if cli_error_type:
                status = CaseRunStatus.FAILED
                error_type = cli_error_type
                error_message = cli_error_message
            elif not execution:
                status = CaseRunStatus.FAILED
                error_type = "NEWMAN_REPORT_MISSING"
                error_message = "newman report did not include this case execution"
            elif assertion_error:
                status = CaseRunStatus.FAILED
                error_type = "NEWMAN_ASSERTION_FAILED"
                error_message = assertion_error
            elif item.expectedStatusCode is not None and response_code != int(item.expectedStatusCode):
                status = CaseRunStatus.FAILED
                error_type = "NEWMAN_STATUS_MISMATCH"
                error_message = f"expected HTTP {int(item.expectedStatusCode)}, got {response_code}"
            duration_ms = _response_time_ms(execution)
            if duration_ms <= 0:
                duration_ms = max((fallback_end_ts - fallback_start_ts) * 1000, 0)
            logs = [line for line in [f"status={response_code}" if response_code else "", error_message or ""] if line]
            results.append(
                CaseRunResult(
                    caseRunId=item.caseRunId,
                    status=status,
                    startAt=fallback_start_ts,
                    endAt=fallback_end_ts,
                    errorType=error_type,
                    errorMessage=error_message,
                    logs=logs,
                    artifacts=artifacts,
                    metrics=CaseRunMetrics(durationMs=duration_ms),
                )
            )
        return results


def execute_newman_job(job: JobPayload) -> NewmanExecutionOutput:
    settings = get_settings()
    workspace_root = Path(settings.runner_workspace_root) if settings.runner_workspace_root else None
    newman_command = str(getattr(settings, "runner_newman_command", "") or "newman").strip() or "newman"
    return NewmanRunnerService(workspace_root=workspace_root, newman_command=newman_command).execute(job)
