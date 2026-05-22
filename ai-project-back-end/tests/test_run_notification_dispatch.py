from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql
from sqlalchemy import Update

from app.api.deps import CurrentUser
from app.models.enums import JobStatus, RunStatus, WorkerStatus
from app.models.prompt_template import PromptTemplate
from app.services import integration_delivery, run as run_service, worker as worker_service
from app.services.provider_registry import register_notification_provider, register_webhook_provider
from app.services.worker import CurrentWorker


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _ScalarsRowsResult:
    class _Scalars:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self._Scalars(self._rows)


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _DeliveryDummyDb:
    def __init__(self, *, notifications: list[object], project_name: str = "WeiTesting"):
        self.notifications = notifications
        self.project_name = project_name
        self.execute_calls = 0
        self.added = []
        self.flushed = False
        self.statements = []

    async def scalar(self, stmt):
        return SimpleNamespace(name=self.project_name)

    async def execute(self, stmt):
        self.execute_calls += 1
        self.statements.append(stmt)
        if self.execute_calls == 1:
            return _ScalarResult(2)  # failed count
        if self.execute_calls == 2:
            return _ScalarResult(8)  # passed count
        if self.execute_calls == 3:
            return _ScalarResult(10)  # total count
        return _ScalarsRowsResult(self.notifications)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


class _RunCancelDummyDb:
    def __init__(self, run_obj):
        self.run_obj = run_obj
        self.executed = 0
        self.added = []
        self.flushed = False

    async def scalar(self, stmt):
        return self.run_obj

    async def execute(self, stmt):
        self.executed += 1
        return None

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


@dataclass
class _WorkerDbState:
    db_worker: object
    job: object
    run: object


class _WorkerDummyDb:
    def __init__(self, state: _WorkerDbState):
        self.state = state
        self.scalar_calls = 0
        self.execute_calls = 0
        self.flushed = False

    async def scalar(self, stmt):
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            return self.state.db_worker
        if self.scalar_calls == 2:
            return self.state.job
        if self.scalar_calls == 3:
            return self.state.run
        return None

    async def execute(self, stmt):
        self.execute_calls += 1
        if self.execute_calls == 1:
            return _ScalarsRowsResult([])
        if self.execute_calls == 2:
            return _RowsResult([])
        return _ScalarResult(0)

    async def flush(self):
        self.flushed = True


class _OutboxConsumerDb:
    class _Rows:
        class _Scalars:
            def __init__(self, rows):
                self._rows = rows

            def all(self):
                return self._rows

        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self._Scalars(self._rows)

    def __init__(self, rows):
        self.rows = rows
        self.flushed = False
        self.last_stmt = None

    async def execute(self, stmt):
        self.last_stmt = stmt
        return self._Rows(self.rows)

    async def flush(self):
        self.flushed = True


def test_dispatch_run_terminal_notification_records_result(monkeypatch) -> None:
    notify_id = uuid.uuid4()
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=notify_id,
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={"events": ["RUN_FAILED"]},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=1,
            status_code=200,
            duration_ms=10,
            error=None,
        ),
    )

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["event"] == "RUN_FAILED"
    assert terminal["sent"] == 1
    assert terminal["failed"] == 0
    assert run_obj.summary_json["notificationDispatchedAt"]


def test_dispatch_run_terminal_notification_scope_env_filtered(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={"events": ["RUN_FAILED"], "rolloutScope": {"envIds": [str(uuid.uuid4())]}},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    called = {"value": False}

    def _provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=10, error=None)

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _provider)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["skipped"] == 1
    assert terminal["sent"] == 0
    assert called["value"] is False
    assert terminal["results"][0]["reason"] == "scope_filtered"
    assert terminal["results"][0]["scopeReason"] == "scope_env_filtered"


def test_dispatch_run_terminal_notification_scope_trigger_filtered(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={"events": ["RUN_FAILED"], "rolloutScope": {"triggerTypes": ["CRON"]}},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    called = {"value": False}

    def _provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=10, error=None)

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _provider)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["skipped"] == 1
    assert terminal["results"][0]["reason"] == "scope_filtered"
    assert terminal["results"][0]["scopeReason"] == "scope_trigger_filtered"
    assert called["value"] is False


def test_dispatch_run_terminal_notification_scope_meta_tag_filtered(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        summary_json={"meta": {"tags": ["smoke"]}},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={"events": ["RUN_FAILED"], "rolloutScope": {"metaTags": ["release"]}},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    called = {"value": False}

    def _provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=10, error=None)

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _provider)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["skipped"] == 1
    assert terminal["results"][0]["reason"] == "scope_filtered"
    assert terminal["results"][0]["scopeReason"] == "scope_meta_tag_filtered"
    assert called["value"] is False


def test_dispatch_run_terminal_notification_scope_batch_percent_filters_some(monkeypatch) -> None:
    run_id = uuid.uuid4()
    run_obj = SimpleNamespace(
        id=run_id,
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        summary_json={"meta": {"tags": ["smoke"]}},
    )

    rules = [
        SimpleNamespace(
            id=uuid.uuid4(),
            channel="WEBHOOK",
            target=f"https://hooks.example.com/{idx}",
            rule_json={"events": ["RUN_FAILED"], "rolloutScope": {"batchPercent": 1}},
        )
        for idx in range(50)
    ]
    db = _DeliveryDummyDb(notifications=rules, project_name="DemoProject")

    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=5, error=None),
    )
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    scope_filtered_count = sum(
        1
        for item in terminal["results"]
        if item.get("reason") == "scope_filtered" and item.get("scopeReason") == "scope_batch_filtered"
    )
    assert scope_filtered_count >= 1
    assert terminal["skipped"] >= 1


def test_dispatch_run_terminal_notification_scope_matched_still_sends(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="CRON",
        status=RunStatus.FAILED,
        summary_json={"meta": {"tags": ["smoke", "release"]}},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={
            "events": ["RUN_FAILED"],
            "rolloutScope": {
                "envIds": [str(run_obj.env_id)],
                "triggerTypes": ["CRON"],
                "metaTags": ["release"],
                "batchPercent": 100,
            },
        },
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=5, error=None),
    )
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["sent"] == 1
    assert terminal["failed"] == 0
    assert terminal["skipped"] == 0
    assert terminal["results"][0]["ok"] is True


def test_dispatch_run_terminal_notification_scope_layer_filtered(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        summary_json={"meta": {"layers": {"releaseRing": "prod"}}},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={
            "events": ["RUN_FAILED"],
            "rolloutScope": {"layerKey": "releaseRing", "layerValues": ["canary"]},
        },
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    called = {"value": False}

    def _provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=10, error=None)

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _provider)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["skipped"] == 1
    assert terminal["results"][0]["reason"] == "scope_filtered"
    assert terminal["results"][0]["scopeReason"] == "scope_layer_filtered"
    assert called["value"] is False


def test_dispatch_run_terminal_notification_scope_time_window_filtered(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        updated_at=datetime(2026, 5, 16, 10, 0, 0),  # Saturday UTC
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={
            "events": ["RUN_FAILED"],
            "rolloutScope": {
                "timeWindow": {
                    "timezoneOffsetMinutes": 0,
                    "weekdays": [1, 2, 3, 4, 5],  # Mon-Fri
                    "startHour": 9,
                    "endHour": 18,
                }
            },
        },
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    called = {"value": False}

    def _provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=10, error=None)

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _provider)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["skipped"] == 1
    assert terminal["results"][0]["reason"] == "scope_filtered"
    assert terminal["results"][0]["scopeReason"] == "scope_time_window_filtered"
    assert called["value"] is False


def test_dispatch_run_terminal_notification_scope_time_window_wrapped_hour_matches(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        updated_at=datetime(2026, 5, 15, 20, 0, 0),  # Friday 20:00 UTC
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={
            "events": ["RUN_FAILED"],
            "rolloutScope": {
                "timeWindow": {
                    "timezoneOffsetMinutes": 0,
                    "weekdays": [5],  # Friday
                    "startHour": 22,
                    "endHour": 6,
                }
            },
        },
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    called = {"value": False}

    def _provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=10, error=None)

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _provider)
    # 20:00 does not match wrapped window [22, 24) U [0, 6)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["skipped"] == 1
    assert terminal["results"][0]["scopeReason"] == "scope_time_window_filtered"

    run_obj.updated_at = datetime(2026, 5, 15, 23, 0, 0)  # Friday 23:00 -> should match
    run_obj.summary_json = {}
    called["value"] = False
    db_2 = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")
    dispatched_2 = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db_2, run=run_obj))
    assert dispatched_2 is True
    terminal_2 = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal_2["sent"] == 1
    assert terminal_2["skipped"] == 0
    assert called["value"] is True


def test_dispatch_run_terminal_notification_time_windows_conflict_pick_priority_then_weight(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        updated_at=datetime(2026, 5, 15, 10, 0, 0),
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={
            "events": ["RUN_FAILED"],
            "rolloutScope": {
                "batchPercent": 100,
                "timeWindows": [
                    {
                        "id": "w-low-priority",
                        "enabled": True,
                        "priority": 20,
                        "weight": 100,
                        "batchPercent": 100,
                        "timeWindow": {"timezoneOffsetMinutes": 0, "weekdays": [5], "startHour": 0, "endHour": 23},
                    },
                    {
                        "id": "w-high-priority-low-weight",
                        "enabled": True,
                        "priority": 10,
                        "weight": 20,
                        "batchPercent": 100,
                        "timeWindow": {"timezoneOffsetMinutes": 0, "weekdays": [5], "startHour": 0, "endHour": 23},
                    },
                    {
                        "id": "w-high-priority-high-weight",
                        "enabled": True,
                        "priority": 10,
                        "weight": 90,
                        "batchPercent": 100,
                        "timeWindow": {"timezoneOffsetMinutes": 0, "weekdays": [5], "startHour": 0, "endHour": 23},
                    },
                ],
            },
        },
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")
    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=8, error=None),
    )
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["sent"] == 1
    decision = terminal["results"][0]["scopeDecision"]
    assert decision["selectedWindowId"] == "w-high-priority-high-weight"
    assert decision["matchedWindowCount"] == 3
    assert decision["reason"] == "window_selected_by_priority_weight_order"


def test_dispatch_run_terminal_notification_time_window_batch_percent_overrides_scope(monkeypatch) -> None:
    run_id = uuid.uuid4()
    selected_notification = None
    filtered_notification = None
    for _ in range(3000):
        candidate = uuid.uuid4()
        if integration_delivery._is_canary_selected(run_id=run_id, notification_id=candidate, percent=1):
            selected_notification = candidate
            break
    for _ in range(3000):
        candidate = uuid.uuid4()
        if not integration_delivery._is_canary_selected(run_id=run_id, notification_id=candidate, percent=1):
            filtered_notification = candidate
            break
    assert selected_notification is not None
    assert filtered_notification is not None

    run_obj = SimpleNamespace(
        id=run_id,
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        updated_at=datetime(2026, 5, 15, 10, 0, 0),
        summary_json={},
    )
    rules = [
        SimpleNamespace(
            id=selected_notification,
            channel="WEBHOOK",
            target="https://hooks.example.com/selected",
            rule_json={
                "events": ["RUN_FAILED"],
                "rolloutScope": {
                    "batchPercent": 100,
                    "timeWindows": [
                        {
                            "id": "narrow-window",
                            "priority": 1,
                            "weight": 1,
                            "batchPercent": 1,
                            "timeWindow": {"timezoneOffsetMinutes": 0, "weekdays": [5], "startHour": 0, "endHour": 23},
                        }
                    ],
                },
            },
        ),
        SimpleNamespace(
            id=filtered_notification,
            channel="WEBHOOK",
            target="https://hooks.example.com/filtered",
            rule_json={
                "events": ["RUN_FAILED"],
                "rolloutScope": {
                    "batchPercent": 100,
                    "timeWindows": [
                        {
                            "id": "narrow-window",
                            "priority": 1,
                            "weight": 1,
                            "batchPercent": 1,
                            "timeWindow": {"timezoneOffsetMinutes": 0, "weekdays": [5], "startHour": 0, "endHour": 23},
                        }
                    ],
                },
            },
        ),
    ]
    db = _DeliveryDummyDb(notifications=rules, project_name="DemoProject")
    called_targets: list[str] = []

    def _provider(**kwargs):
        called_targets.append(str(kwargs["target"]))
        return integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=7, error=None)

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _provider)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["sent"] == 1
    assert terminal["skipped"] == 1
    assert called_targets == ["https://hooks.example.com/selected"]
    filtered = next(item for item in terminal["results"] if item.get("reason") == "scope_filtered")
    assert filtered["scopeReason"] == "scope_batch_filtered"


def test_dispatch_run_terminal_notification_time_windows_no_match_filtered(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        env_id=uuid.uuid4(),
        trigger_type="MANUAL",
        status=RunStatus.FAILED,
        updated_at=datetime(2026, 5, 16, 10, 0, 0),  # Saturday
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={
            "events": ["RUN_FAILED"],
            "rolloutScope": {
                "timeWindows": [
                    {
                        "id": "weekdays-only",
                        "enabled": True,
                        "priority": 10,
                        "weight": 90,
                        "timeWindow": {"timezoneOffsetMinutes": 0, "weekdays": [1, 2, 3, 4, 5], "startHour": 9, "endHour": 18},
                    }
                ]
            },
        },
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")
    called = {"value": False}

    def _provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(ok=True, attempt_count=1, status_code=200, duration_ms=10, error=None)

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _provider)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["skipped"] == 1
    assert terminal["results"][0]["scopeReason"] == "scope_time_window_filtered"
    assert terminal["results"][0]["scopeDecision"]["matchedWindowCount"] == 0
    assert terminal["results"][0]["scopeDecision"]["reason"] == "no_time_window_matched"
    assert called["value"] is False


def test_dispatch_run_terminal_notification_is_idempotent(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.PASSED,
        summary_json={"notificationDispatchedAt": "2026-05-15T12:00:00"},
    )
    db = _DeliveryDummyDb(notifications=[])

    def _should_not_call(**kwargs):
        raise AssertionError("deliver_webhook should not be called for already dispatched run")

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _should_not_call)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is False


def test_dispatch_run_terminal_notification_swallow_delivery_exception(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.CANCELED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    def _raise_error(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(integration_delivery, "deliver_webhook", _raise_error)
    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["failed"] == 1
    assert terminal["results"][0]["error"].startswith("boom")


def test_dispatch_run_terminal_notification_supports_custom_provider() -> None:
    provider_name = f"CUSTOM_{uuid.uuid4().hex[:8].upper()}"
    called = {"value": False}

    def _custom_provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=1,
            status_code=202,
            duration_ms=5,
            error=None,
        )

    register_webhook_provider(provider_name, _custom_provider)

    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/custom",
        rule_json={"events": ["RUN_FAILED"], "provider": provider_name},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    assert called["value"] is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["sent"] == 1
    assert terminal["results"][0]["statusCode"] == 202


def test_dispatch_run_terminal_notification_supports_custom_email_provider() -> None:
    provider_name = f"CUSTOM_EMAIL_{uuid.uuid4().hex[:8].upper()}"
    called = {"value": False}

    def _custom_email_provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=1,
            status_code=202,
            duration_ms=5,
            error=None,
        )

    register_notification_provider("EMAIL", provider_name, _custom_email_provider)

    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="EMAIL",
        target="dev@example.com",
        rule_json={"events": ["RUN_FAILED"], "provider": provider_name},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    assert called["value"] is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["sent"] == 1
    assert terminal["results"][0]["statusCode"] == 202


def test_dispatch_run_terminal_notification_supports_custom_im_provider() -> None:
    provider_name = f"CUSTOM_IM_{uuid.uuid4().hex[:8].upper()}"
    called = {"value": False}

    def _custom_im_provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=1,
            status_code=206,
            duration_ms=4,
            error=None,
        )

    register_notification_provider("IM", provider_name, _custom_im_provider)

    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="IM",
        target="group://robot-room",
        rule_json={"events": ["RUN_FAILED"], "provider": provider_name},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    assert called["value"] is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["sent"] == 1
    assert terminal["results"][0]["statusCode"] == 206


def test_dispatch_run_terminal_notification_uses_dingtalk_provider_and_persists_sent_outbox(monkeypatch) -> None:
    called = {"value": False, "provider_args": None}

    def _stub_dingtalk_provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=2,
            status_code=200,
            duration_ms=11,
            error=None,
        )

    def _fake_get_notification_provider(channel: str, provider_name: str):
        called["provider_args"] = (channel, provider_name)
        if channel == "IM" and provider_name == "DINGTALK":
            return _stub_dingtalk_provider
        return None

    monkeypatch.setattr(integration_delivery, "get_notification_provider", _fake_get_notification_provider)

    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="IM",
        target="group://robot-room",
        rule_json={"events": ["RUN_FAILED"], "provider": "DINGTALK"},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    assert called["value"] is True
    assert called["provider_args"] == ("IM", "DINGTALK")
    assert len(db.added) == 1
    outbox = db.added[0]
    assert outbox.provider == "DINGTALK"
    assert outbox.channel == "IM"
    assert outbox.status == "SENT"
    assert outbox.attempts == 2
    assert outbox.last_status_code == 200
    assert outbox.last_error is None


def test_dispatch_run_terminal_notification_aggregates_multiple_rules() -> None:
    provider_name = f"BATCH_{uuid.uuid4().hex[:8].upper()}"
    called_targets: list[str] = []

    def _custom_provider(**kwargs):
        called_targets.append(str(kwargs["target"]))
        return integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=1,
            status_code=200,
            duration_ms=2,
            error=None,
        )

    register_webhook_provider(provider_name, _custom_provider)
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rules = [
        SimpleNamespace(
            id=uuid.uuid4(),
            channel="WEBHOOK",
            target=f"https://hooks.example.com/{idx}",
            rule_json={"events": ["RUN_FAILED"], "provider": provider_name},
        )
        for idx in range(3)
    ]
    db = _DeliveryDummyDb(notifications=rules, project_name="DemoProject")

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    terminal = run_obj.summary_json["notificationDispatch"]["terminal"]
    assert terminal["sent"] == 3
    assert terminal["failed"] == 0
    assert terminal["skipped"] == 0
    assert len(terminal["results"]) == 3
    assert len(called_targets) == 3


def test_dispatch_run_terminal_notification_uses_versioned_template_reference(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={"events": ["RUN_FAILED"], "templateName": "run_terminal_summary", "templateVersion": "v1"},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    async def _fake_resolve_template(*args, **kwargs):
        return "RUN {{runId}} {{status}}", {
            "mode": "VERSIONED",
            "scene": "NOTIFICATION_WEBHOOK",
            "name": "run_terminal_summary",
            "version": "v1",
        }

    monkeypatch.setattr(integration_delivery, "_resolve_notification_template", _fake_resolve_template)
    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=1,
            status_code=200,
            duration_ms=8,
            error=None,
        ),
    )

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    assert len(db.added) == 1
    outbox = db.added[0]
    summary = str(outbox.payload_json.get("summary") or "")
    assert str(run_obj.id) in summary
    assert "FAILED" in summary
    assert outbox.payload_json.get("templateRef", {}).get("version") == "v1"
    result = run_obj.summary_json["notificationDispatch"]["terminal"]["results"][0]
    assert result.get("templateRef", {}).get("version") == "v1"
    assert "templateReason" not in result


def test_dispatch_run_terminal_notification_fallbacks_when_template_not_found(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        channel="WEBHOOK",
        target="https://hooks.example.com/run",
        rule_json={"events": ["RUN_FAILED"], "templateName": "missing_template", "templateVersion": "v404"},
    )
    db = _DeliveryDummyDb(notifications=[rule], project_name="DemoProject")

    async def _fake_resolve_template(*args, **kwargs):
        return None, None

    monkeypatch.setattr(integration_delivery, "_resolve_notification_template", _fake_resolve_template)
    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=1,
            status_code=200,
            duration_ms=7,
            error=None,
        ),
    )

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    assert len(db.added) == 1
    outbox = db.added[0]
    assert "summary" not in outbox.payload_json
    result = run_obj.summary_json["notificationDispatch"]["terminal"]["results"][0]
    assert result["ok"] is True
    assert result.get("templateReason") == "template_not_found"


def test_resolve_notification_template_canary_split_selection() -> None:
    tenant_id = uuid.uuid4()
    project_id = uuid.uuid4()
    run_id = uuid.uuid4()
    active = PromptTemplate(
        tenant_id=tenant_id,
        project_id=project_id,
        scene="NOTIFICATION_WEBHOOK",
        name="run_terminal_summary",
        version="v-active",
        content="ACTIVE {{runId}}",
        variables_json={},
        is_active=True,
    )
    canary = PromptTemplate(
        tenant_id=tenant_id,
        project_id=project_id,
        scene="NOTIFICATION_WEBHOOK",
        name="run_terminal_summary",
        version="v-canary",
        content="CANARY {{runId}}",
        variables_json={},
        is_active=False,
    )

    canary_notification_id = None
    active_notification_id = None
    for _ in range(2000):
        candidate = uuid.uuid4()
        if integration_delivery._is_canary_selected(run_id=run_id, notification_id=candidate, percent=50):
            canary_notification_id = candidate
            break
    for _ in range(2000):
        candidate = uuid.uuid4()
        if not integration_delivery._is_canary_selected(run_id=run_id, notification_id=candidate, percent=50):
            active_notification_id = candidate
            break
    assert canary_notification_id is not None
    assert active_notification_id is not None

    class _TemplateDb:
        def __init__(self, sequence):
            self._sequence = list(sequence)

        async def scalar(self, stmt):
            if not self._sequence:
                return None
            return self._sequence.pop(0)

    rule_json = {
        "templateName": "run_terminal_summary",
        "templateStrategy": "CANARY",
        "templateCanaryVersion": "v-canary",
        "templateCanaryPercent": 50,
    }
    canary_db = _TemplateDb([active, canary])
    canary_template, canary_ref = asyncio.run(
        integration_delivery._resolve_notification_template(
            canary_db,
            tenant_id=tenant_id,
            project_id=project_id,
            channel="WEBHOOK",
            rule_json=rule_json,
            run_id=run_id,
            notification_id=canary_notification_id,
        )
    )
    assert canary_template and "CANARY" in canary_template
    assert canary_ref is not None
    assert canary_ref["mode"] == "CANARY"
    assert canary_ref["selectedVersion"] == "v-canary"
    assert canary_ref["activeVersion"] == "v-active"
    assert canary_ref["canaryVersion"] == "v-canary"

    active_db = _TemplateDb([active])
    active_template, active_ref = asyncio.run(
        integration_delivery._resolve_notification_template(
            active_db,
            tenant_id=tenant_id,
            project_id=project_id,
            channel="WEBHOOK",
            rule_json=rule_json,
            run_id=run_id,
            notification_id=active_notification_id,
        )
    )
    assert active_template and "ACTIVE" in active_template
    assert active_ref is not None
    assert active_ref["mode"] == "ACTIVE"
    assert active_ref["selectedVersion"] == "v-active"
    assert active_ref["activeVersion"] == "v-active"
    assert active_ref["canaryVersion"] == "v-canary"


def test_dispatch_run_terminal_notification_auto_rollback_triggers_at_threshold(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rules = [
        SimpleNamespace(
            id=uuid.uuid4(),
            channel="WEBHOOK",
            target=f"https://hooks.example.com/{idx}",
            rule_json={
                "events": ["RUN_FAILED"],
                "templateName": "run_terminal_summary",
                "templateStrategy": "CANARY",
                "templateCanaryVersion": "v-canary",
                "templateCanaryPercent": 100,
                "autoRollbackEnabled": True,
                "autoRollbackFailureThreshold": 3,
            },
        )
        for idx in range(3)
    ]
    db = _DeliveryDummyDb(notifications=rules, project_name="DemoProject")

    async def _fake_resolve_template(*args, **kwargs):
        return "CANARY {{runId}}", {
            "mode": "CANARY",
            "scene": "NOTIFICATION_WEBHOOK",
            "name": "run_terminal_summary",
            "version": "v-canary",
            "selectedVersion": "v-canary",
            "canaryVersion": "v-canary",
            "activeVersion": "v-active",
        }

    monkeypatch.setattr(integration_delivery, "_resolve_notification_template", _fake_resolve_template)
    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(
            ok=False,
            attempt_count=1,
            status_code=500,
            duration_ms=5,
            error="HTTP 500",
        ),
    )

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    auto_rollback = run_obj.summary_json["notificationDispatch"]["terminal"]["autoRollback"]
    assert auto_rollback["triggered"] is True
    assert auto_rollback["reason"] == "threshold_reached"
    assert auto_rollback["actions"][0]["activeVersion"] == "v-active"
    assert auto_rollback["actions"][0]["canaryVersion"] == "v-canary"
    update_stmts = [stmt for stmt in db.statements if isinstance(stmt, Update)]
    assert len(update_stmts) == 2


def test_dispatch_run_terminal_notification_auto_rollback_not_triggered_below_threshold(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=RunStatus.FAILED,
        summary_json={},
    )
    rules = [
        SimpleNamespace(
            id=uuid.uuid4(),
            channel="WEBHOOK",
            target=f"https://hooks.example.com/{idx}",
            rule_json={
                "events": ["RUN_FAILED"],
                "templateName": "run_terminal_summary",
                "templateStrategy": "CANARY",
                "templateCanaryVersion": "v-canary",
                "templateCanaryPercent": 100,
                "autoRollbackEnabled": True,
                "autoRollbackFailureThreshold": 3,
            },
        )
        for idx in range(2)
    ]
    db = _DeliveryDummyDb(notifications=rules, project_name="DemoProject")

    async def _fake_resolve_template(*args, **kwargs):
        return "CANARY {{runId}}", {
            "mode": "CANARY",
            "scene": "NOTIFICATION_WEBHOOK",
            "name": "run_terminal_summary",
            "version": "v-canary",
            "selectedVersion": "v-canary",
            "canaryVersion": "v-canary",
            "activeVersion": "v-active",
        }

    monkeypatch.setattr(integration_delivery, "_resolve_notification_template", _fake_resolve_template)
    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(
            ok=False,
            attempt_count=1,
            status_code=500,
            duration_ms=5,
            error="HTTP 500",
        ),
    )

    dispatched = asyncio.run(integration_delivery.dispatch_run_terminal_notification(db, run=run_obj))
    assert dispatched is True
    auto_rollback = run_obj.summary_json["notificationDispatch"]["terminal"]["autoRollback"]
    assert auto_rollback["triggered"] is False
    assert auto_rollback["reason"] == "threshold_not_reached"
    assert auto_rollback["actions"][0]["failureCount"] == 2
    update_stmts = [stmt for stmt in db.statements if isinstance(stmt, Update)]
    assert len(update_stmts) == 0


def test_cancel_run_dispatches_notification_even_when_delivery_fails(monkeypatch) -> None:
    run_obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        status=RunStatus.RUNNING,
        end_at=None,
        summary_json={},
    )
    db = _RunCancelDummyDb(run_obj=run_obj)
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )

    async def _fake_get_project(*args, **kwargs):
        return SimpleNamespace(id=run_obj.project_id, owner_id=user.id)

    async def _fake_require_write(*args, **kwargs):
        return None

    async def _raise_delivery(*args, **kwargs):
        raise RuntimeError("notify failed")

    monkeypatch.setattr(run_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(run_service, "_require_project_write", _fake_require_write)
    monkeypatch.setattr(run_service, "dispatch_run_terminal_notification", _raise_delivery)

    canceled = asyncio.run(run_service.cancel_run(db, user=user, run_id=run_obj.id))
    assert canceled is run_obj
    assert run_obj.status == RunStatus.CANCELED
    assert any(getattr(row, "action", None) == "CANCEL_RUN" for row in db.added)
    assert db.flushed is True


def test_worker_report_job_result_dispatches_on_terminal(monkeypatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    worker_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    run_id = uuid.uuid4()
    job_id = uuid.uuid4()
    db_worker = SimpleNamespace(id=worker_id, tenant_id=tenant_id, last_seen_at=None, status=WorkerStatus.ONLINE)
    job = SimpleNamespace(id=job_id, run_id=run_id, tenant_id=tenant_id, worker_id=None, meta_json={"items": []}, end_at=None, status=JobStatus.QUEUED)
    run_obj = SimpleNamespace(id=run_id, tenant_id=tenant_id, status=RunStatus.RUNNING, end_at=None, summary_json={})
    db = _WorkerDummyDb(state=_WorkerDbState(db_worker=db_worker, job=job, run=run_obj))

    called = {"value": False}

    async def _fake_dispatch(*args, **kwargs):
        called["value"] = True
        return True

    monkeypatch.setattr(worker_service, "dispatch_run_terminal_notification", _fake_dispatch)

    worker = CurrentWorker(id=worker_id, tenant_id=tenant_id, capabilities=frozenset({"API"}))
    asyncio.run(
        worker_service.report_job_result(
            db,
            worker=worker,
            worker_id=str(worker_id),
            run_id=run_id,
            job_id=job_id,
            results=[],
            job_status=JobStatus.CANCELED,
        )
    )
    assert called["value"] is True
    assert run_obj.status == RunStatus.CANCELED
    assert db.flushed is True


def test_process_due_notification_deliveries_marks_sent(monkeypatch) -> None:
    outbox = SimpleNamespace(
        id=uuid.uuid4(),
        target="https://hooks.example.com/outbox",
        provider="WEBHOOK",
        payload_json={"runId": "1"},
        rule_json={},
        attempts=0,
        max_retries=3,
        status="QUEUED",
        next_retry_at=None,
        last_status_code=None,
        last_duration_ms=0,
        last_error=None,
    )
    db = _OutboxConsumerDb([outbox])

    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=1,
            status_code=200,
            duration_ms=6,
            error=None,
        ),
    )
    processed = asyncio.run(integration_delivery.process_due_notification_deliveries(db, batch_size=10, retry_base_seconds=2))
    assert processed == 1
    assert outbox.status == "SENT"
    assert outbox.attempts == 1
    assert outbox.next_retry_at is None
    assert db.flushed is True


def test_process_due_notification_deliveries_uses_skip_locked_query() -> None:
    db = _OutboxConsumerDb([])
    processed = asyncio.run(integration_delivery.process_due_notification_deliveries(db, batch_size=10, retry_base_seconds=2))
    assert processed == 0
    assert db.last_stmt is not None
    sql = str(db.last_stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})).upper()
    assert "FOR UPDATE" in sql
    assert "SKIP LOCKED" in sql


def test_process_notification_outbox_item_requeues_with_backoff(monkeypatch) -> None:
    outbox = SimpleNamespace(
        id=uuid.uuid4(),
        target="https://hooks.example.com/outbox",
        provider="WEBHOOK",
        payload_json={"runId": "1"},
        rule_json={},
        attempts=0,
        max_retries=3,
        status="QUEUED",
        next_retry_at=None,
        last_status_code=None,
        last_duration_ms=0,
        last_error=None,
    )
    db = _OutboxConsumerDb([])
    fixed_now = datetime(2026, 5, 16, 10, 0, 0)

    monkeypatch.setattr(
        integration_delivery,
        "deliver_webhook",
        lambda **kwargs: integration_delivery.DeliveryResult(
            ok=False,
            attempt_count=1,
            status_code=500,
            duration_ms=9,
            error="HTTP 500",
        ),
    )
    monkeypatch.setattr(integration_delivery, "_utcnow", lambda: fixed_now)

    asyncio.run(integration_delivery.process_notification_outbox_item(db, outbox=outbox, retry_base_seconds=3))
    assert outbox.status == "QUEUED"
    assert outbox.attempts == 1
    assert outbox.next_retry_at is not None
    assert int((outbox.next_retry_at - fixed_now).total_seconds()) == 3


def test_process_notification_outbox_item_supports_channel_aware_provider() -> None:
    provider_name = f"IM_PROVIDER_{uuid.uuid4().hex[:8].upper()}"
    called = {"value": False}

    def _custom_provider(**kwargs):
        called["value"] = True
        return integration_delivery.DeliveryResult(
            ok=True,
            attempt_count=1,
            status_code=200,
            duration_ms=5,
            error=None,
        )

    register_notification_provider("IM", provider_name, _custom_provider)
    outbox = SimpleNamespace(
        id=uuid.uuid4(),
        channel="IM",
        target="group://ops",
        provider=provider_name,
        payload_json={"runId": "1"},
        rule_json={},
        attempts=0,
        max_retries=2,
        status="QUEUED",
        next_retry_at=None,
        last_status_code=None,
        last_duration_ms=0,
        last_error=None,
    )
    db = _OutboxConsumerDb([])

    asyncio.run(integration_delivery.process_notification_outbox_item(db, outbox=outbox, retry_base_seconds=2))
    assert called["value"] is True
    assert outbox.status == "SENT"


def test_simulate_rollout_scope_prefers_priority_then_weight_then_array_order() -> None:
    notification_id = uuid.uuid4()
    run_context = {
        "envId": str(uuid.uuid4()),
        "triggerType": "MANUAL",
        "weekday": 5,
        "hour": 10,
        "seed": "fixed-seed",
    }
    rollout_scope = {
        "batchPercent": 100,
        "timeWindows": [
            {
                "id": "w-low-priority",
                "enabled": True,
                "priority": 20,
                "weight": 100,
                "batchPercent": 100,
                "timeWindow": {"weekdays": [5], "startHour": 9, "endHour": 18},
            },
            {
                "id": "w-high-priority-low-weight",
                "enabled": True,
                "priority": 10,
                "weight": 20,
                "batchPercent": 100,
                "timeWindow": {"weekdays": [5], "startHour": 9, "endHour": 18},
            },
            {
                "id": "w-high-priority-high-weight",
                "enabled": True,
                "priority": 10,
                "weight": 90,
                "batchPercent": 100,
                "timeWindow": {"weekdays": [5], "startHour": 9, "endHour": 18},
            },
        ],
    }
    result = integration_delivery.simulate_rollout_scope(
        notification_id=notification_id,
        rollout_scope=rollout_scope,
        run_context=run_context,
    )
    assert result.matched is True
    assert result.scope_decision.get("selectedWindowId") == "w-high-priority-high-weight"
    assert result.scope_decision.get("matchedWindowCount") == 3
    assert any("selected timeWindow w-high-priority-high-weight by priority/weight" == item for item in result.explanations)
    assert len(result.conflict_candidates) == 3
    assert result.conflict_candidates[0]["id"] == "w-low-priority"


def test_simulate_rollout_scope_returns_scope_filtered_reason_when_not_matched() -> None:
    notification_id = uuid.uuid4()
    run_context = {"envId": str(uuid.uuid4()), "seed": "fixed-seed"}
    rollout_scope = {"envIds": [str(uuid.uuid4())], "batchPercent": 100}
    result = integration_delivery.simulate_rollout_scope(
        notification_id=notification_id,
        rollout_scope=rollout_scope,
        run_context=run_context,
    )
    assert result.matched is False
    assert result.scope_reason == "scope_env_filtered"
    assert "env filtered" in result.explanations


def test_simulate_rollout_scope_time_window_batch_percent_overrides_global() -> None:
    notification_id = uuid.uuid4()
    run_context = {"weekday": 5, "hour": 10, "seed": "fixed-seed"}
    rollout_scope = {
        "batchPercent": 100,
        "timeWindows": [
            {
                "id": "w1",
                "enabled": True,
                "priority": 10,
                "weight": 20,
                "batchPercent": 35,
                "timeWindow": {"weekdays": [5], "startHour": 9, "endHour": 18},
            }
        ],
    }
    result = integration_delivery.simulate_rollout_scope(
        notification_id=notification_id,
        rollout_scope=rollout_scope,
        run_context=run_context,
    )
    assert result.resolved_batch_percent == 35
