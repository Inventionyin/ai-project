from __future__ import annotations

import json
import platform
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.core.config import get_settings
from app.models.enums import ArtifactType, CaseRunStatus, JobStatus
from app.schemas.run import ArtifactIndex, CaseRunMetrics, CaseRunResult
from app.schemas.worker import JobPayload

_SENSITIVE_HEADER_KEYS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
}


def _mask_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    masked: dict[str, str] = {}
    for key, value in headers.items():
        if str(key).strip().lower() in _SENSITIVE_HEADER_KEYS:
            masked[str(key)] = "******"
        else:
            masked[str(key)] = str(value)
    return masked


@dataclass(frozen=True, slots=True)
class PytestAllureExecutionOutput:
    job_status: JobStatus
    results: list[CaseRunResult]
    workspace: Path


@dataclass(frozen=True, slots=True)
class _GeneratedCase:
    case_run_id: str
    test_file: Path


@dataclass(frozen=True, slots=True)
class _CaseExecutionOutput:
    case_run_id: str
    start_ts: int
    end_ts: int
    return_code: int
    stdout: str
    stderr: str
    error_message: str


class PytestAllureRunnerService:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        python_executable: str = "python",
        allure_command: str = "allure",
    ) -> None:
        self._workspace_root = workspace_root
        self._python_executable = python_executable
        self._allure_command = allure_command

    def execute(self, job: JobPayload) -> PytestAllureExecutionOutput:
        workspace, generated_cases = self._prepare_workspace(job)
        allure_results_dir = workspace / "allure-results"
        self._prepare_allure_metadata(job=job, allure_results_dir=allure_results_dir)
        execution_log = workspace / "execution.log"
        timeout_sec = max(int(job.suiteConfig.timeoutSec), 1)
        case_outputs: list[_CaseExecutionOutput] = []
        logs: list[str] = []
        for generated in generated_cases:
            case_start = int(time.time())
            pytest_cmd: Sequence[str] = (
                self._python_executable,
                "-m",
                "pytest",
                str(generated.test_file),
                f"--alluredir={allure_results_dir}",
                "-q",
            )
            error_message = ""
            try:
                completed = subprocess.run(
                    pytest_cmd,
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                completed = subprocess.CompletedProcess(
                    args=pytest_cmd,
                    returncode=1,
                    stdout=(exc.stdout or ""),
                    stderr=(exc.stderr or ""),
                )
                error_message = "pytest_timeout"
            case_end = int(time.time())
            case_output = _CaseExecutionOutput(
                case_run_id=generated.case_run_id,
                start_ts=case_start,
                end_ts=case_end,
                return_code=int(completed.returncode),
                stdout=str(completed.stdout or ""),
                stderr=str(completed.stderr or ""),
                error_message=error_message,
            )
            case_outputs.append(case_output)
            logs.append(
                "\n".join(
                    [
                        f"[caseRunId={generated.case_run_id}] returnCode={case_output.return_code}",
                        case_output.stdout,
                        case_output.stderr,
                    ]
                ).strip()
            )
        report_dir = self._generate_allure_report(workspace, allure_results_dir, timeout_sec=timeout_sec)
        execution_log.write_text("\n\n".join(logs).strip(), encoding="utf-8")
        allure_zip = self._zip_allure_results(allure_results_dir)
        allure_report_zip = self._zip_allure_report(report_dir)
        artifacts = self._build_artifacts(execution_log, allure_zip, allure_report_zip)
        results = self._build_case_results(case_outputs=case_outputs, artifacts=artifacts)
        job_status = JobStatus.DONE if all(item.return_code == 0 for item in case_outputs) else JobStatus.FAILED
        return PytestAllureExecutionOutput(job_status=job_status, results=results, workspace=workspace)

    def _prepare_workspace(self, job: JobPayload) -> tuple[Path, list[_GeneratedCase]]:
        root = self._workspace_root or Path(tempfile.gettempdir()) / "ai-test-platform-runners"
        root.mkdir(parents=True, exist_ok=True)
        workspace = Path(tempfile.mkdtemp(prefix=f"job-{job.jobId}-", dir=root))
        tests_dir = workspace / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        params_path = workspace / "job-params.json"
        params_path.write_text(
            json.dumps(
                {
                    "jobId": job.jobId,
                    "runId": job.runId,
                    "env": job.env.model_dump(mode="json"),
                    "items": [item.model_dump(mode="json") for item in job.items],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        generated_cases: list[_GeneratedCase] = []
        for index, item in enumerate(job.items, start=1):
            test_file = tests_dir / f"test_case_{index:04d}_{item.caseRunId.replace('-', '_')}.py"
            method = str(item.apiMethod or "GET").strip().upper() or "GET"
            api_url = str(item.apiUrl or "").strip()
            headers = {str(k): str(v) for k, v in dict(item.headers or {}).items()}
            masked_headers = _mask_sensitive_headers(headers)
            test_file.write_text(
                "\n".join(
                    [
                        "import json",
                        "from urllib.parse import urljoin",
                        "import allure",
                        "import requests",
                        "",
                        f"@allure.title('Case {item.caseRunId}')",
                        f"def test_case_{index:04d}():",
                        f"    method = {json.dumps(method, ensure_ascii=False)}",
                        f"    api_url = {json.dumps(api_url, ensure_ascii=False)}",
                        f"    base_url = {json.dumps(str(job.env.baseUrl or ''), ensure_ascii=False)}",
                        f"    params = {json.dumps(dict(item.params or {}), ensure_ascii=False)}",
                        f"    headers = {json.dumps(headers, ensure_ascii=False)}",
                        f"    masked_headers = {json.dumps(masked_headers, ensure_ascii=False)}",
                        "    assert api_url",
                        "    full_url = api_url if api_url.startswith(('http://', 'https://')) else urljoin(base_url.rstrip('/') + '/', api_url.lstrip('/'))",
                        "    if method in ('GET', 'DELETE', 'HEAD', 'OPTIONS'):",
                        "        response = requests.request(method=method, url=full_url, params=params, headers=headers, timeout=30)",
                        "    else:",
                        "        response = requests.request(method=method, url=full_url, json=params, headers=headers, timeout=30)",
                        "    allure.attach(json.dumps({'method': method, 'url': full_url, 'params': params, 'headers': masked_headers}, ensure_ascii=False, indent=2), 'request', allure.attachment_type.JSON)",
                        "    allure.attach(response.text[:20000], 'response_body', allure.attachment_type.TEXT)",
                        "    assert 200 <= int(response.status_code) < 400",
                    ]
                ),
                encoding="utf-8",
            )
            generated_cases.append(_GeneratedCase(case_run_id=item.caseRunId, test_file=test_file))
        return workspace, generated_cases

    def _prepare_allure_metadata(self, *, job: JobPayload, allure_results_dir: Path) -> None:
        allure_results_dir.mkdir(parents=True, exist_ok=True)
        env_lines = [
            f"baseUrl={job.env.baseUrl}",
            f"runId={job.runId}",
            f"jobId={job.jobId}",
            f"timeoutSec={int(job.suiteConfig.timeoutSec)}",
            f"retryCount={int(job.suiteConfig.retryCount)}",
            f"host={platform.node() or 'unknown'}",
            f"os={platform.system()} {platform.release()}".strip(),
            f"python={platform.python_version()}",
        ]
        for key in sorted(job.env.variables.keys()):
            env_lines.append(f"env.{key}={job.env.variables[key]}")
        (allure_results_dir / "environment.properties").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
        executor_payload = {
            "name": "AI Testing Platform",
            "type": "pytest",
            "buildName": f"Run {job.runId}",
            "buildOrder": int(time.time()),
            "reportName": f"Allure Report - {job.runId}",
        }
        (allure_results_dir / "executor.json").write_text(
            json.dumps(executor_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _zip_allure_results(self, allure_results_dir: Path) -> Path | None:
        if not allure_results_dir.exists():
            return None
        zip_path = allure_results_dir.parent / "allure-results.zip"
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for child in allure_results_dir.rglob("*"):
                if child.is_file():
                    zf.write(child, child.relative_to(allure_results_dir.parent))
        return zip_path

    def _zip_allure_report(self, report_dir: Path | None) -> Path | None:
        if report_dir is None or not report_dir.exists():
            return None
        zip_path = report_dir.parent / "allure-report.zip"
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for child in report_dir.rglob("*"):
                if child.is_file():
                    zf.write(child, child.relative_to(report_dir.parent))
        return zip_path

    def _generate_allure_report(self, workspace: Path, allure_results_dir: Path, *, timeout_sec: int) -> Path | None:
        if not allure_results_dir.exists():
            return None
        report_dir = workspace / "allure-report"
        try:
            subprocess.run(
                [
                    self._allure_command,
                    "generate",
                    str(allure_results_dir),
                    "-o",
                    str(report_dir),
                    "--clean",
                ],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=max(timeout_sec, 1),
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if not report_dir.exists():
            return None
        return report_dir

    def _build_artifacts(
        self, execution_log: Path, allure_zip: Path | None, allure_report_zip: Path | None
    ) -> list[ArtifactIndex]:
        artifacts: list[ArtifactIndex] = []
        if execution_log.exists():
            artifacts.append(
                ArtifactIndex(
                    type=ArtifactType.LOG_BUNDLE,
                    storageKey=str(execution_log),
                    meta={"name": "execution.log", "kind": "EXECUTION_LOG", "size": execution_log.stat().st_size},
                )
            )
        if allure_zip is not None and allure_zip.exists():
            artifacts.append(
                ArtifactIndex(
                    type=ArtifactType.LOG_BUNDLE,
                    storageKey=str(allure_zip),
                    meta={"name": "allure-results.zip", "kind": "ALLURE_RESULTS", "size": allure_zip.stat().st_size},
                )
            )
        if allure_report_zip is not None and allure_report_zip.exists():
            artifacts.append(
                ArtifactIndex(
                    type=ArtifactType.LOG_BUNDLE,
                    storageKey=str(allure_report_zip),
                    meta={"name": "allure-report.zip", "kind": "ALLURE_REPORT", "size": allure_report_zip.stat().st_size},
                )
            )
        return artifacts

    def _build_case_results(
        self,
        *,
        case_outputs: list[_CaseExecutionOutput],
        artifacts: list[ArtifactIndex],
    ) -> list[CaseRunResult]:
        results: list[CaseRunResult] = []
        for item in case_outputs:
            status = CaseRunStatus.PASSED if item.return_code == 0 else CaseRunStatus.FAILED
            duration_ms = max((item.end_ts - item.start_ts) * 1000, 0)
            error_message = item.error_message or (item.stderr or "").strip()
            error_message = error_message[:2000] if error_message else None
            logs = [line for line in f"{item.stdout}\n{item.stderr}".splitlines() if line][:200]
            results.append(
                CaseRunResult(
                    caseRunId=item.case_run_id,
                    status=status,
                    startAt=item.start_ts,
                    endAt=item.end_ts,
                    errorType="RUNNER_ERROR" if status == CaseRunStatus.FAILED else None,
                    errorMessage=error_message,
                    logs=logs,
                    artifacts=artifacts,
                    metrics=CaseRunMetrics(durationMs=duration_ms),
                )
            )
        return results


def execute_pytest_allure_job(job: JobPayload) -> PytestAllureExecutionOutput:
    settings = get_settings()
    workspace_root = Path(settings.runner_workspace_root) if settings.runner_workspace_root else None
    return PytestAllureRunnerService(
        workspace_root=workspace_root,
        python_executable=settings.runner_python_executable,
        allure_command=settings.runner_allure_command,
    ).execute(job)
