from __future__ import annotations

from pathlib import Path

from app.models.enums import CaseRunStatus, JobStatus, TestCaseType as _TestCaseType
from app.schemas.worker import JobEnv, JobExecution, JobItem, JobPayload, JobSuiteConfig
from app.services.run import _resolve_runner_type
from app.services.runner_default_http import DefaultHttpRunnerService
from app.services.runner_dispatch import dispatch_job_runner


def _job(*, expected_status_code: int | None = 200) -> JobPayload:
    return JobPayload(
        jobId="job-http-1",
        runId="run-http-1",
        env=JobEnv(baseUrl="https://api.example.test", variables={"userId": "42"}, secrets={}),
        suiteConfig=JobSuiteConfig(timeoutSec=5, retryCount=0, failFast=False),
        execution=JobExecution(runnerType="DEFAULT"),
        items=[
            JobItem(
                caseRunId="cr-1",
                testcaseId="tc-1",
                testCaseId="TC_API_001",
                type=_TestCaseType.API,
                contentMd="GET /users should return ok",
                apiMethod="GET",
                apiUrl="/users/{{userId}}",
                params={"verbose": True},
                headers={"X-Trace": "trace-1"},
                expectedResult='"ok"',
                expectedStatusCode=expected_status_code,
            )
        ],
    )


def test_default_http_runner_executes_api_case(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Response:
        status_code = 200
        text = '{"status":"ok"}'
        headers = {"Content-Type": "application/json"}

    def fake_request(*, method, url, params=None, json=None, headers=None, timeout=None):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = params
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("app.services.runner_default_http.requests.request", fake_request)

    output = DefaultHttpRunnerService(workspace_root=tmp_path).execute(_job())

    assert output.job_status == JobStatus.DONE
    assert output.results[0].status == CaseRunStatus.PASSED
    assert output.results[0].metrics and output.results[0].metrics.durationMs >= 0
    assert captured["method"] == "GET"
    assert captured["url"] == "https://api.example.test/users/42"
    assert captured["params"] == {"verbose": True}
    assert captured["headers"] == {"X-Trace": "trace-1"}
    assert captured["timeout"] == 5


def test_default_http_runner_marks_status_assertion_failure(tmp_path, monkeypatch) -> None:
    class _Response:
        status_code = 500
        text = '{"status":"error"}'
        headers = {"Content-Type": "application/json"}

    def fake_request(**kwargs):
        return _Response()

    monkeypatch.setattr("app.services.runner_default_http.requests.request", fake_request)

    output = DefaultHttpRunnerService(workspace_root=tmp_path).execute(_job(expected_status_code=200))

    assert output.job_status == JobStatus.FAILED
    assert output.results[0].status == CaseRunStatus.FAILED
    assert output.results[0].errorType == "HTTP_ASSERT_FAIL"
    assert "expected HTTP 200" in (output.results[0].errorMessage or "")


def test_dispatch_handles_default_http_runner(monkeypatch) -> None:
    from app.schemas.run import CaseRunResult
    from app.services import runner_dispatch
    from app.services.runner_default_http import DefaultHttpExecutionOutput

    def fake_execute(job):
        return DefaultHttpExecutionOutput(
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

    monkeypatch.setattr(runner_dispatch, "execute_default_http_job", fake_execute)

    result = dispatch_job_runner(_job())

    assert result.handled is True
    assert result.output is not None
    assert _resolve_runner_type({"runnerType": "DEFAULT"}) == "DEFAULT"
