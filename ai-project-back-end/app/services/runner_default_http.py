from __future__ import annotations

import json
import platform
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests

from app.core.config import get_settings
from app.models.enums import ArtifactType, CaseRunStatus, JobStatus
from app.schemas.run import ArtifactIndex, CaseRunMetrics, CaseRunResult
from app.schemas.worker import JobItem, JobPayload
from app.services.runner_pytest_allure import _order_job_items

_VAR_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}|\$\{([^{}]+?)\}")
_QUERY_METHODS = {"GET", "DELETE", "HEAD", "OPTIONS"}


@dataclass(frozen=True, slots=True)
class DefaultHttpExecutionOutput:
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


def _placeholder_name(match: re.Match[str]) -> str:
    return str(match.group(1) or match.group(2) or "").strip()


def _lookup(name: str, context: dict[str, object]) -> object | None:
    key = str(name or "").strip()
    if not key:
        return None
    if key.startswith("env."):
        return context.get(key[4:])
    return context.get(key)


def _render(value: object, context: dict[str, object]) -> object:
    if isinstance(value, str):
        matched = _VAR_RE.fullmatch(value)
        if matched:
            return _lookup(_placeholder_name(matched), context)

        def _replace(inner: re.Match[str]) -> str:
            resolved = _lookup(_placeholder_name(inner), context)
            return "" if resolved is None else str(resolved)

        return _VAR_RE.sub(_replace, value)
    if isinstance(value, dict):
        return {str(k): _render(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, context) for v in value]
    return value


def _merge_url(base_url: str, api_url: str) -> str:
    raw = str(api_url or "").strip()
    if raw.startswith(("http://", "https://")):
        return raw
    base = str(base_url or "").strip()
    if not base:
        return raw
    return urljoin(base.rstrip("/") + "/", raw.lstrip("/"))


def _artifact(path: Path, *, artifact_type: ArtifactType, kind: str) -> ArtifactIndex | None:
    if not path.exists():
        return None
    return ArtifactIndex(
        type=artifact_type,
        storageKey=str(path),
        meta={"name": path.name, "kind": kind, "size": path.stat().st_size},
    )


def _build_failure_result(
    item: JobItem,
    *,
    start_at: int,
    end_at: int,
    error_type: str,
    error_message: str,
    log_lines: list[str],
) -> CaseRunResult:
    return CaseRunResult(
        caseRunId=item.caseRunId,
        status=CaseRunStatus.FAILED,
        startAt=start_at,
        endAt=end_at,
        errorType=error_type,
        errorMessage=error_message[:2000],
        logs=log_lines[:1000],
        artifacts=[],
        metrics=CaseRunMetrics(durationMs=max(0, (end_at - start_at) * 1000)),
    )


class DefaultHttpRunnerService:
    def __init__(self, *, workspace_root: Path | None = None) -> None:
        self._workspace_root = (workspace_root or _default_runner_root()).expanduser()

    def execute(self, job: JobPayload) -> DefaultHttpExecutionOutput:
        ordered_items = [item for item in _order_job_items(job.items) if isinstance(item, JobItem)]
        workspace = self._workspace_root / f"default-http-{job.runId}-{job.jobId}"
        workspace.mkdir(parents=True, exist_ok=True)

        context: dict[str, object] = {
            **{str(k): v for k, v in dict(job.env.variables or {}).items()},
            **{str(k): v for k, v in dict(job.env.secrets or {}).items()},
        }

        results: list[CaseRunResult] = []
        has_failure = False
        timeout_sec = max(1, int(job.suiteConfig.timeoutSec or 30))

        for index, item in enumerate(ordered_items, start=1):
            started_at = time.time()
            started_ts = int(started_at)
            method = str(item.apiMethod or "").strip().upper() or "GET"
            api_url = str(item.apiUrl or "").strip()
            log_lines = [f"case={item.caseRunId}", f"method={method}", f"apiUrl={api_url}"]
            if not api_url:
                finished_ts = int(time.time())
                has_failure = True
                results.append(
                    _build_failure_result(
                        item,
                        start_at=started_ts,
                        end_at=finished_ts,
                        error_type="API_URL_MISSING",
                        error_message="apiUrl is required for DEFAULT HTTP runner",
                        log_lines=log_lines,
                    )
                )
                continue

            rendered_url = _render(api_url, context)
            full_url = _merge_url(str(job.env.baseUrl), "" if rendered_url is None else str(rendered_url))
            rendered_params = _render(dict(item.params or {}), context)
            rendered_headers = _render(dict(item.headers or {}), context)
            params_final = rendered_params if isinstance(rendered_params, dict) else {}
            headers_final = {str(k): str(v) for k, v in dict(rendered_headers or {}).items()}

            request_kwargs: dict[str, object] = {
                "method": method,
                "url": full_url,
                "headers": headers_final,
                "timeout": timeout_sec,
            }
            if method in _QUERY_METHODS:
                request_kwargs["params"] = params_final
            else:
                request_kwargs["json"] = params_final

            snapshot_path = workspace / f"{index:04d}-{item.caseRunId}-exchange.json"
            log_path = workspace / f"{index:04d}-{item.caseRunId}.log"
            try:
                response = requests.request(**request_kwargs)
                duration_ms = int((time.time() - started_at) * 1000)
                finished_ts = int(time.time())
                body_text = response.text[:20000]
                log_lines.extend([f"url={full_url}", f"status={response.status_code}", f"durationMs={duration_ms}"])

                snapshot_path.write_text(
                    json.dumps(
                        {
                            "request": {
                                "method": method,
                                "url": full_url,
                                "params": params_final if method in _QUERY_METHODS else None,
                                "json": params_final if method not in _QUERY_METHODS else None,
                                "headers": headers_final,
                            },
                            "response": {
                                "statusCode": response.status_code,
                                "headers": dict(response.headers or {}),
                                "body": body_text,
                            },
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                log_path.write_text("\n".join(log_lines), encoding="utf-8")

                status_ok = (
                    int(response.status_code) == int(item.expectedStatusCode)
                    if item.expectedStatusCode is not None
                    else 200 <= int(response.status_code) < 400
                )
                body_ok = True
                expected_result = str(item.expectedResult or "").strip()
                if expected_result:
                    body_ok = expected_result in body_text

                artifacts = [
                    artifact
                    for artifact in (
                        _artifact(snapshot_path, artifact_type=ArtifactType.API_EXCHANGE, kind="REQUEST_RESPONSE_SNAPSHOT"),
                        _artifact(log_path, artifact_type=ArtifactType.LOG_BUNDLE, kind="EXECUTION_LOG"),
                    )
                    if artifact is not None
                ]

                if status_ok and body_ok:
                    results.append(
                        CaseRunResult(
                            caseRunId=item.caseRunId,
                            status=CaseRunStatus.PASSED,
                            startAt=started_ts,
                            endAt=finished_ts,
                            logs=log_lines[:1000],
                            artifacts=artifacts,
                            metrics=CaseRunMetrics(durationMs=duration_ms),
                        )
                    )
                    continue

                has_failure = True
                error_message = (
                    f"expected HTTP {int(item.expectedStatusCode)}, got {int(response.status_code)}"
                    if not status_ok and item.expectedStatusCode is not None
                    else f"unexpected HTTP {int(response.status_code)}"
                    if not status_ok
                    else f"expected result not found: {expected_result}"
                )
                results.append(
                    CaseRunResult(
                        caseRunId=item.caseRunId,
                        status=CaseRunStatus.FAILED,
                        startAt=started_ts,
                        endAt=finished_ts,
                        errorType="HTTP_ASSERT_FAIL" if not status_ok else "EXPECTED_RESULT_NOT_FOUND",
                        errorMessage=error_message[:2000],
                        logs=log_lines[:1000],
                        artifacts=artifacts,
                        metrics=CaseRunMetrics(durationMs=duration_ms),
                    )
                )
            except requests.exceptions.Timeout as exc:
                finished_ts = int(time.time())
                has_failure = True
                log_path.write_text("\n".join(log_lines + [f"timeout={exc}"]), encoding="utf-8")
                results.append(
                    _build_failure_result(
                        item,
                        start_at=started_ts,
                        end_at=finished_ts,
                        error_type="REQUEST_TIMEOUT",
                        error_message=str(exc),
                        log_lines=log_lines + [str(exc)],
                    )
                )
            except requests.exceptions.ConnectionError as exc:
                finished_ts = int(time.time())
                has_failure = True
                log_path.write_text("\n".join(log_lines + [f"connection={exc}"]), encoding="utf-8")
                results.append(
                    _build_failure_result(
                        item,
                        start_at=started_ts,
                        end_at=finished_ts,
                        error_type="REQUEST_CONNECTION_ERROR",
                        error_message=str(exc),
                        log_lines=log_lines + [str(exc)],
                    )
                )
            except requests.exceptions.RequestException as exc:
                finished_ts = int(time.time())
                has_failure = True
                log_path.write_text("\n".join(log_lines + [f"request={exc}"]), encoding="utf-8")
                results.append(
                    _build_failure_result(
                        item,
                        start_at=started_ts,
                        end_at=finished_ts,
                        error_type="REQUEST_ERROR",
                        error_message=str(exc),
                        log_lines=log_lines + [str(exc)],
                    )
                )

        return DefaultHttpExecutionOutput(
            job_status=JobStatus.FAILED if has_failure else JobStatus.DONE,
            results=results,
            workspace=workspace,
        )


def execute_default_http_job(job: JobPayload) -> DefaultHttpExecutionOutput:
    return DefaultHttpRunnerService().execute(job)
