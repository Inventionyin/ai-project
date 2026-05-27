from __future__ import annotations

from pathlib import Path

from scripts.run_api_worker import WorkerClient


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return dict(self._payload)


class _FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, *, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse(self.payload)


class _QueuedSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def post(self, url, *, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if not self.payloads:
            raise AssertionError("unexpected extra post")
        return _FakeResponse(self.payloads.pop(0))


def test_worker_client_accepts_api_success_code_zero(tmp_path: Path) -> None:
    session = _FakeSession({"code": 0, "message": "ok", "data": {"workerId": "wid", "token": "tok"}})
    client = WorkerClient(
        api_base_url="http://127.0.0.1:8000",
        tenant_id="tenant-1",
        worker_name="worker-a",
        capabilities=["API"],
        slots=1,
        version="1.0.0",
        state_path=tmp_path / "worker-state.json",
        session=session,
    )

    state = client.ensure_registered()

    assert state.worker_id == "wid"
    assert state.token == "tok"
    assert session.calls[0]["url"] == "http://127.0.0.1:8000/api/workers/register"


def test_worker_client_report_uses_existing_state_without_reregister(tmp_path: Path) -> None:
    state_path = tmp_path / "worker-state.json"
    state_path.write_text('{"workerId":"wid","token":"tok"}', encoding="utf-8")
    session = _QueuedSession([{"code": 0, "message": "ok", "data": {}}])
    client = WorkerClient(
        api_base_url="http://127.0.0.1:8000",
        tenant_id="tenant-1",
        worker_name="worker-a",
        capabilities=["API"],
        slots=1,
        version="1.0.0",
        state_path=state_path,
        session=session,
    )

    client.report(
        job=type("Job", (), {"jobId": "job-1", "runId": "run-1", "items": [], "execution": type("Execution", (), {"runnerType": "DEFAULT"})()})(),
        job_status=type("JobStatusProxy", (), {"value": "DONE"})(),
        results=[],
    )

    assert [call["url"] for call in session.calls] == ["http://127.0.0.1:8000/api/workers/report"]
    assert session.calls[0]["headers"] == {"Authorization": "Bearer tok"}
