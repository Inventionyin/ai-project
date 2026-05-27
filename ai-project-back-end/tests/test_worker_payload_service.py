from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.models.enums import JobStatus, RunStatus, TestCaseType as _TestCaseType, WorkerStatus
from app.services import worker as worker_service
from app.services.worker import CurrentWorker


class _ScalarListResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class _RowsResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


class _PollJobDb:
    def __init__(self, *, db_worker, job, run, env, testcase_rows) -> None:
        self.db_worker = db_worker
        self.job = job
        self.run = run
        self.env = env
        self.testcase_rows = testcase_rows
        self.execute_calls = 0
        self.flush_called = False

    async def scalar(self, _statement):
        if not hasattr(self, "_scalar_calls"):
            self._scalar_calls = 0
        self._scalar_calls += 1
        if self._scalar_calls == 1:
            return self.db_worker
        if self._scalar_calls == 2:
            return self.run
        if self._scalar_calls == 3:
            return self.env
        raise AssertionError(f"unexpected scalar call #{self._scalar_calls}")

    async def execute(self, _statement):
        self.execute_calls += 1
        if self.execute_calls == 1:
            return _ScalarListResult([self.job])
        if self.execute_calls == 2:
            return _RowsResult([])
        if self.execute_calls == 3:
            return _RowsResult(self.testcase_rows)
        raise AssertionError(f"unexpected execute call #{self.execute_calls}")

    async def flush(self) -> None:
        self.flush_called = True


def test_poll_job_enriches_missing_suite_api_fields_from_testcase() -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    worker_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    run_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    job_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    case_run_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    testcase_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    env_id = uuid.UUID("66666666-6666-6666-6666-666666666666")

    db_worker = SimpleNamespace(
        id=worker_id,
        tenant_id=tenant_id,
        last_seen_at=None,
        status=WorkerStatus.ONLINE,
        capabilities_json=["API"],
    )
    job = SimpleNamespace(
        id=job_id,
        run_id=run_id,
        tenant_id=tenant_id,
        worker_id=None,
        status=JobStatus.QUEUED,
        start_at=None,
        created_at=None,
        meta_json={
            "envId": str(env_id),
            "items": [
                {
                    "caseRunId": str(case_run_id),
                    "testcaseId": str(testcase_id),
                    "type": "API",
                    "params": {"tenant": "suite"},
                }
            ],
        },
    )
    run = SimpleNamespace(id=run_id, tenant_id=tenant_id, status=RunStatus.QUEUED, start_at=None, env_id=env_id)
    env = SimpleNamespace(
        id=env_id,
        tenant_id=tenant_id,
        base_url="https://api.example.test",
        variables_json={"region": "apac"},
        secrets_ref=None,
    )
    testcase_rows = [
        (
            testcase_id,
            "GET /health should return ok",
            "TC_API_001",
            _TestCaseType.API,
            "GET",
            "/health",
            {
                "apiParams": {"fromCase": "yes"},
                "apiHeaders": {"X-Test": "suite"},
                "expectedResult": "ok",
                "expectedStatusCode": 200,
                "preconditions": "none",
                "postconditions": "none",
            },
        )
    ]
    db = _PollJobDb(db_worker=db_worker, job=job, run=run, env=env, testcase_rows=testcase_rows)
    worker = CurrentWorker(id=worker_id, tenant_id=tenant_id, capabilities=frozenset({"API"}))

    payload = asyncio.run(
        worker_service.poll_job(
            db,
            worker=worker,
            worker_id=str(worker_id),
            capabilities=["API"],
        )
    )

    assert payload.job is not None
    item = payload.job.items[0]
    assert item.testcaseId == str(testcase_id)
    assert item.testCaseId == "TC_API_001"
    assert item.type == _TestCaseType.API
    assert item.apiMethod == "GET"
    assert item.apiUrl == "/health"
    assert item.params == {"fromCase": "yes", "tenant": "suite"}
    assert item.headers == {"X-Test": "suite"}
    assert item.expectedResult == "ok"
    assert item.expectedStatusCode == 200
    assert item.preconditions == "none"
    assert item.postconditions == "none"
    assert db.flush_called is True
