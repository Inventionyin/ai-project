from __future__ import annotations

from dataclasses import dataclass

from app.schemas.worker import JobPayload
from app.services.runner_pytest_allure import PytestAllureExecutionOutput, execute_pytest_allure_job

_RUNNER_TYPE_PYTEST_ALLURE = "PYTEST_ALLURE"


@dataclass(frozen=True, slots=True)
class RunnerDispatchResult:
    handled: bool
    output: PytestAllureExecutionOutput | None = None


def dispatch_job_runner(job: JobPayload) -> RunnerDispatchResult:
    runner_type = str(job.execution.runnerType or "").strip().upper()
    if runner_type == _RUNNER_TYPE_PYTEST_ALLURE:
        return RunnerDispatchResult(handled=True, output=execute_pytest_allure_job(job))
    return RunnerDispatchResult(handled=False, output=None)
