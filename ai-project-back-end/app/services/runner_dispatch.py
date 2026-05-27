from __future__ import annotations

from dataclasses import dataclass

from app.schemas.worker import JobPayload
from app.services.runner_default_http import DefaultHttpExecutionOutput, execute_default_http_job
from app.services.runner_pytest_allure import PytestAllureExecutionOutput, execute_pytest_allure_job
from app.services.runner_newman import NewmanExecutionOutput, execute_newman_job

_RUNNER_TYPE_DEFAULT = "DEFAULT"
_RUNNER_TYPE_PYTEST_ALLURE = "PYTEST_ALLURE"
_RUNNER_TYPE_NEWMAN = "NEWMAN"


@dataclass(frozen=True, slots=True)
class RunnerDispatchResult:
    handled: bool
    output: DefaultHttpExecutionOutput | PytestAllureExecutionOutput | NewmanExecutionOutput | None = None


def dispatch_job_runner(job: JobPayload) -> RunnerDispatchResult:
    runner_type = str(job.execution.runnerType or "").strip().upper()
    if runner_type == _RUNNER_TYPE_DEFAULT:
        return RunnerDispatchResult(handled=True, output=execute_default_http_job(job))
    if runner_type == _RUNNER_TYPE_PYTEST_ALLURE:
        return RunnerDispatchResult(handled=True, output=execute_pytest_allure_job(job))
    if runner_type == _RUNNER_TYPE_NEWMAN:
        return RunnerDispatchResult(handled=True, output=execute_newman_job(job))
    return RunnerDispatchResult(handled=False, output=None)
