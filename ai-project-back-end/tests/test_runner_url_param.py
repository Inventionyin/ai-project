from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from app.models.enums import TestCaseType as _TestCaseType
from app.schemas.worker import JobEnv, JobItem, JobPayload, JobSuiteConfig
from app.services.runner_pytest_allure import PytestAllureRunnerService


def test_prepare_workspace_renders_api_url_before_join() -> None:
    with TemporaryDirectory() as td:
        workspace_root = Path(td)
        svc = PytestAllureRunnerService(workspace_root=workspace_root)
        job = JobPayload(
            jobId="job-1",
            runId="run-1",
            env=JobEnv(baseUrl="http://example.com", variables={}, secrets={}),
            suiteConfig=JobSuiteConfig(timeoutSec=3, retryCount=0, failFast=False),
            items=[
                JobItem(
                    caseRunId="cr-1",
                    testcaseId="tc-1",
                    testCaseId="TC_1",
                    type=_TestCaseType.API,
                    contentMd="x",
                    apiMethod="GET",
                    apiUrl="/users/${id}",
                    params={},
                    headers={},
                    expectedResult="",
                    expectedStatusCode=200,
                    preconditions="",
                    postconditions="",
                )
            ],
        )

        workspace, generated = svc._prepare_workspace(job)
        assert len(generated) == 1
        (workspace / "context.json").write_text(json.dumps({"vars": {"id": 123}, "status": {}}, ensure_ascii=False), encoding="utf-8")

        allure_stub = types.ModuleType("allure")

        class _AttachType:
            JSON = "json"
            TEXT = "text"

        def _title(_: str):
            def _decorator(fn):
                return fn

            return _decorator

        def _attach(*_: Any, **__: Any) -> None:
            return None

        allure_stub.attachment_type = _AttachType
        allure_stub.title = _title
        allure_stub.attach = _attach
        sys.modules["allure"] = allure_stub

        called: dict[str, Any] = {}

        def _request(*, method: str, url: str, **_: Any):
            called["method"] = method
            called["url"] = url

            class _Resp:
                status_code = 200
                text = "{}"

                def json(self):
                    return {}

            return _Resp()

        test_file = generated[0].test_file
        import importlib.util

        module_spec = importlib.util.spec_from_file_location("generated_case", test_file)
        assert module_spec and module_spec.loader
        mod = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(mod)

        mod.requests.request = _request
        mod.test_case_0001()

        assert called["method"] == "GET"
        assert called["url"] == "http://example.com/users/123"
