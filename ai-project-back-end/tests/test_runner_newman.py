from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.models.enums import CaseRunStatus, JobStatus, TestCaseType
from app.schemas.worker import JobEnv, JobExecution, JobItem, JobPayload, JobSuiteConfig
from app.services.run import _resolve_runner_type, normalize_ci_token_policy
from app.services.runner_dispatch import dispatch_job_runner
from app.services.runner_newman import NewmanRunnerService


def _job(*, case_run_id: str = "cr-1", expected_status_code: int | None = 200) -> JobPayload:
    return JobPayload(
        jobId="job-1",
        runId="run-1",
        env=JobEnv(
            baseUrl="https://api.example.test",
            variables={"token": "abc123"},
            secrets={"secretToken": ""},
        ),
        suiteConfig=JobSuiteConfig(timeoutSec=5, retryCount=0, failFast=False),
        execution=JobExecution(runnerType="NEWMAN"),
        items=[
            JobItem(
                caseRunId=case_run_id,
                testcaseId="tc-1",
                testCaseId="TC_API_001",
                type=TestCaseType.API,
                contentMd="GET user detail",
                apiMethod="GET",
                apiUrl="/users/{{userId}}",
                params={"userId": "42", "verbose": True},
                headers={"Authorization": "Bearer {{token}}", "X-Trace": "trace-1"},
                expectedResult='"name"',
                expectedStatusCode=expected_status_code,
            )
        ],
    )


def test_newman_runner_builds_collection_and_maps_success(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd, *, cwd, capture_output, text, timeout, check):
        captured["cmd"] = list(cmd)
        captured["cwd"] = str(cwd)
        export_path = Path(cmd[cmd.index("--reporter-json-export") + 1])
        export_path.write_text(
            json.dumps(
                {
                    "run": {
                        "executions": [
                            {
                                "item": {"name": "TC_API_001"},
                                "response": {
                                    "code": 200,
                                    "status": "OK",
                                    "responseTime": 123,
                                    "body": '{"name":"Ada"}',
                                },
                                "assertions": [],
                            }
                        ]
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="newman ok", stderr="")

    monkeypatch.setattr("app.services.runner_newman.subprocess.run", fake_run)

    output = NewmanRunnerService(workspace_root=tmp_path, newman_command="newman").execute(_job())

    assert output.job_status == JobStatus.DONE
    assert [result.status for result in output.results] == [CaseRunStatus.PASSED]
    assert output.results[0].metrics and output.results[0].metrics.durationMs == 123
    assert (output.workspace / "collection.json").exists()
    assert (output.workspace / "environment.json").exists()
    assert captured["cmd"][:2] == ["newman", "run"]
    artifact_names = {str(artifact.meta.get("name")) for artifact in output.results[0].artifacts}
    assert {"execution.log", "newman-report.json"}.issubset(artifact_names)


def test_newman_runner_maps_failed_assertion(tmp_path: Path, monkeypatch) -> None:
    def fake_run(cmd, *, cwd, capture_output, text, timeout, check):
        export_path = Path(cmd[cmd.index("--reporter-json-export") + 1])
        export_path.write_text(
            json.dumps(
                {
                    "run": {
                        "executions": [
                            {
                                "item": {"name": "TC_API_001"},
                                "response": {"code": 500, "status": "Internal Server Error", "responseTime": 50},
                                "assertions": [
                                    {"assertion": "expected status 200", "error": {"message": "expected 500 to equal 200"}}
                                ],
                            }
                        ],
                        "failures": [
                            {"source": {"name": "TC_API_001"}, "error": {"message": "expected 500 to equal 200"}}
                        ],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="assertion failed")

    monkeypatch.setattr("app.services.runner_newman.subprocess.run", fake_run)

    output = NewmanRunnerService(workspace_root=tmp_path, newman_command="newman").execute(_job())

    assert output.job_status == JobStatus.FAILED
    assert output.results[0].status == CaseRunStatus.FAILED
    assert output.results[0].errorType == "NEWMAN_ASSERTION_FAILED"
    assert "expected 500 to equal 200" in (output.results[0].errorMessage or "")


def test_newman_runner_missing_cli_fails_cases_cleanly(tmp_path: Path, monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("newman")

    monkeypatch.setattr("app.services.runner_newman.subprocess.run", fake_run)

    output = NewmanRunnerService(workspace_root=tmp_path, newman_command="newman").execute(_job())

    assert output.job_status == JobStatus.FAILED
    assert output.results[0].status == CaseRunStatus.FAILED
    assert output.results[0].errorType == "NEWMAN_NOT_FOUND"


def test_dispatch_and_ci_policy_accept_newman(monkeypatch) -> None:
    from app.models.enums import JobStatus
    from app.schemas.run import CaseRunResult
    from app.services import runner_dispatch
    from app.services.runner_newman import NewmanExecutionOutput

    def fake_execute(job):
        return NewmanExecutionOutput(
            job_status=JobStatus.DONE,
            results=[
                CaseRunResult(
                    caseRunId="cr-1",
                    status=CaseRunStatus.PASSED,
                    startAt=1,
                    endAt=2,
                )
            ],
            workspace=Path("work"),
        )

    monkeypatch.setattr(runner_dispatch, "execute_newman_job", fake_execute)

    result = dispatch_job_runner(_job())

    assert result.handled is True
    assert result.output is not None
    assert _resolve_runner_type({"runnerType": "NEWMAN"}) == "NEWMAN"
    assert normalize_ci_token_policy({"allowedRunnerTypes": ["newman", "DEFAULT", "newman"]})[
        "allowedRunnerTypes"
    ] == ["NEWMAN", "DEFAULT"]
