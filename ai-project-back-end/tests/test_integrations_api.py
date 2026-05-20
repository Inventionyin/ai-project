from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient
import anyio

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import integrations as integrations_endpoint
from app.core.database import get_db
from app.models.enums import ProjectRole
from app.models.integration import Notification
from app.models.integration import NotificationOutbox
from app.models.project import Project
from app.models.prompt_template import PromptTemplate
from app.schemas.integration import NotificationConfigDetail
from app.schemas.integration import NotificationDeliveryListData, NotificationDeliveryListItem, NotificationDeliveryRetryResult
from app.schemas.integration import NotificationDiagnosticsCheck, NotificationDiagnosticsData, NotificationDiagnosticsFailure, NotificationDiagnosticsProviderReadiness, NotificationDiagnosticsSummary
from app.schemas.integration import NotificationStrategyCenterDeliveryStats, NotificationStrategyCenterFilterReasonStats, NotificationStrategyCenterItem
from app.services import integration_config


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(integrations_endpoint.router, prefix="/api")

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def _notification_detail(project_id: uuid.UUID, notification_id: uuid.UUID) -> NotificationConfigDetail:
    return NotificationConfigDetail(
        id=str(notification_id),
        projectId=str(project_id),
        channel="WEBHOOK",
        target="https://hooks.example.com/notify",
        rule={"events": ["RUN_FAILED"]},
        enabled=True,
        createdAt=1710000000,
    )


def test_notifications_create_and_list_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    notification_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_create(db, *, user, project_id, payload):
        assert payload.channel == "WEBHOOK"
        assert payload.enabled is True
        return _notification_detail(project_id, notification_id)

    async def _fake_list(db, *, user, project_id):
        return [_notification_detail(project_id, notification_id)]

    monkeypatch.setattr(integrations_endpoint, "create_notification_config", _fake_create)
    monkeypatch.setattr(integrations_endpoint, "list_notification_configs", _fake_list)

    client = TestClient(_build_app())
    create_resp = client.post(
        f"/api/projects/{project_id}/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {"events": ["RUN_FAILED"]},
            "enabled": True,
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["id"] == str(notification_id)
    assert create_resp.json()["data"]["channel"] == "WEBHOOK"

    list_resp = client.get(f"/api/projects/{project_id}/integrations/notifications")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["code"] == 0
    assert len(body["data"]) == 1
    assert body["data"][0]["target"] == "https://hooks.example.com/notify"


@dataclass
class _ScalarResult:
    value: object

    def scalar_one_or_none(self):
        return self.value


class _ScalarsResult:
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


class _ViewerWriteDeniedDb:
    async def scalar(self, stmt):
        if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Project:
            return Project(
                id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                name="proj",
                owner_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            )
        return None

    async def execute(self, stmt):
        text = str(stmt)
        if "project_members.role" in text:
            return _ScalarResult(ProjectRole.VIEWER)
        return _ScalarResult(None)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _CreateNotificationDb:
    def __init__(self, *, prompt_templates: list[PromptTemplate] | None = None) -> None:
        self._created: Notification | None = None
        self._prompt_templates = prompt_templates or []

    async def scalar(self, stmt):
        if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Project:
            return Project(
                id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                name="proj",
                owner_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            )
        if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is PromptTemplate:
            return self._match_prompt_template(stmt)
        return None

    def _match_prompt_template(self, stmt):
        params = stmt.compile().params
        tenant_id = next((value for key, value in params.items() if key.startswith("tenant_id_")), None)
        project_id = next((value for key, value in params.items() if key.startswith("project_id_")), None)
        scene = next((value for key, value in params.items() if key.startswith("scene_")), None)
        name = next((value for key, value in params.items() if key.startswith("name_")), None)
        version = next((value for key, value in params.items() if key.startswith("version_")), None)
        require_active = "prompt_templates.is_active IS true" in str(stmt)

        for template in self._prompt_templates:
            if tenant_id is not None and template.tenant_id != tenant_id:
                continue
            if project_id is not None and template.project_id != project_id:
                continue
            if scene is not None and template.scene != scene:
                continue
            if name is not None and template.name != name:
                continue
            if version is not None and template.version != version:
                continue
            if require_active and not template.is_active:
                continue
            return template.id
        return None

    def add(self, row) -> None:
        self._created = row

    async def flush(self) -> None:
        if self._created is not None:
            if getattr(self._created, "id", None) is None:
                self._created.id = uuid.UUID("33333333-3333-3333-3333-333333333333")
            if getattr(self._created, "created_at", None) is None:
                self._created.created_at = datetime.now(UTC)

    async def delete(self, row) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _default_prompt_template(
    *,
    name: str,
    version: str,
    is_active: bool,
    scene: str = "NOTIFICATION_WEBHOOK",
) -> PromptTemplate:
    return PromptTemplate(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        scene=scene,
        name=name,
        version=version,
        content="Run {{runId}} {{status}}",
        variables_json={},
        is_active=is_active,
    )


def _build_create_app(*, db: _CreateNotificationDb | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(integrations_endpoint.router, prefix="/api")
    create_db = db or _CreateNotificationDb(
        prompt_templates=[
            _default_prompt_template(name="run_terminal_summary", version="v1", is_active=True),
            _default_prompt_template(name="run_terminal_summary_inactive", version="v1", is_active=False),
        ]
    )

    async def _override_db():
        yield create_db

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def _build_existing_notification() -> Notification:
    return Notification(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        channel="WEBHOOK",
        target="https://hooks.example.com/notify",
        rule_json={"events": ["RUN_FAILED"]},
        enabled=True,
        created_at=datetime.now(UTC),
    )


class _UpdateNotificationDb(_CreateNotificationDb):
    def __init__(
        self,
        *,
        notification: Notification | None = None,
        prompt_templates: list[PromptTemplate] | None = None,
    ) -> None:
        super().__init__(prompt_templates=prompt_templates)
        self._notification = notification or _build_existing_notification()

    async def scalar(self, stmt):
        if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Notification:
            return self._notification
        return await super().scalar(stmt)


def _build_update_app(*, db: _UpdateNotificationDb | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(integrations_endpoint.router, prefix="/api")
    update_db = db or _UpdateNotificationDb(
        prompt_templates=[_default_prompt_template(name="run_terminal_summary", version="v1", is_active=True)]
    )

    async def _override_db():
        yield update_db

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_notifications_create_forbidden_for_viewer() -> None:
    app = FastAPI()
    app.include_router(integrations_endpoint.router, prefix="/api")

    async def _override_db():
        yield _ViewerWriteDeniedDb()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset(),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    client = TestClient(app)
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {"events": ["RUN_FAILED"]},
            "enabled": True,
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Only Owner/Editor can modify this project"


def test_notifications_create_rejects_invalid_events() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {"events": ["BAD_EVENT"]},
            "enabled": True,
        },
    )
    assert resp.status_code in (400, 422)


def test_notifications_create_accepts_valid_rollout_scope() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "events": ["RUN_FAILED"],
                "rolloutScope": {
                    "envIds": [
                        "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA",
                        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    ],
                    "triggerTypes": ["manual", "CRON", "manual"],
                    "metaTags": [" smoke ", "release", "smoke"],
                    "batchPercent": 25,
                },
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    rollout_scope = resp.json()["data"]["rule"]["rolloutScope"]
    assert rollout_scope["envIds"] == ["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]
    assert rollout_scope["triggerTypes"] == ["MANUAL", "CRON"]
    assert rollout_scope["metaTags"] == ["smoke", "release"]
    assert rollout_scope["batchPercent"] == 25


def test_notifications_create_rejects_invalid_rollout_scope_env_ids() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "rolloutScope": {
                    "envIds": ["not-a-uuid"],
                }
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422


def test_notifications_create_accepts_rollout_scope_layer_and_time_window() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "events": ["RUN_FAILED"],
                "rolloutScope": {
                    "layerKey": "releaseRing",
                    "layerValues": [" canary ", "prod", "CANARY"],
                    "priority": 7,
                    "timeWindow": {
                        "timezoneOffsetMinutes": 480,
                        "weekdays": [1, 2, 2, 7],
                        "startHour": 9,
                        "endHour": 18,
                    },
                },
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    rollout_scope = resp.json()["data"]["rule"]["rolloutScope"]
    assert rollout_scope["layerKey"] == "releaseRing"
    assert rollout_scope["layerValues"] == ["canary", "prod"]
    assert rollout_scope["priority"] == 7
    assert rollout_scope["timeWindow"]["timezoneOffsetMinutes"] == 480
    assert rollout_scope["timeWindow"]["weekdays"] == [1, 2, 7]
    assert rollout_scope["timeWindow"]["startHour"] == 9
    assert rollout_scope["timeWindow"]["endHour"] == 18


def test_notifications_create_rejects_rollout_scope_layer_without_values() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "rolloutScope": {
                    "layerKey": "releaseRing",
                }
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "layerValues is required" in resp.json()["detail"]


def test_notifications_create_rejects_rollout_scope_time_window_range() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "rolloutScope": {
                    "timeWindow": {
                        "timezoneOffsetMinutes": 9999,
                    }
                }
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "timezoneOffsetMinutes" in resp.json()["detail"]


def test_notifications_create_rejects_invalid_rollout_scope_trigger_types() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "rolloutScope": {
                    "triggerTypes": ["manual", "pipeline"],
                }
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "rolloutScope.triggerTypes" in resp.json()["detail"]


def test_notifications_create_rejects_invalid_rollout_scope_batch_percent() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "rolloutScope": {
                    "batchPercent": 0,
                }
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "rolloutScope.batchPercent" in resp.json()["detail"]


def test_notifications_create_accepts_rollout_scope_time_windows() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "rolloutScope": {
                    "batchPercent": 60,
                    "timeWindows": [
                        {
                            "id": "work-hour-window",
                            "enabled": True,
                            "priority": 8,
                            "weight": 80,
                            "batchPercent": 20,
                            "timeWindow": {
                                "timezoneOffsetMinutes": 480,
                                "weekdays": [1, 2, 3, 4, 5],
                                "startHour": 9,
                                "endHour": 18,
                            },
                        },
                        {
                            "enabled": False,
                            "priority": 9,
                            "weight": 60,
                            "timeWindow": {"weekdays": [6, 7]},
                        },
                    ],
                }
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    windows = resp.json()["data"]["rule"]["rolloutScope"]["timeWindows"]
    assert len(windows) == 2
    assert windows[0]["id"] == "work-hour-window"
    assert windows[0]["priority"] == 8
    assert windows[0]["weight"] == 80
    assert windows[0]["batchPercent"] == 20
    assert windows[1]["enabled"] is False


def test_notifications_create_rejects_invalid_rollout_scope_time_windows() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "rolloutScope": {
                    "timeWindows": [
                        {
                            "id": " ",
                            "priority": 0,
                            "weight": 101,
                            "batchPercent": 0,
                            "timeWindow": {"startHour": 9},
                        }
                    ]
                }
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "rolloutScope.timeWindows" in resp.json()["detail"]


def test_notifications_create_rejects_invalid_template_variable() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {"template": "Run {{unknownVar}} failed"},
            "enabled": True,
        },
    )
    assert resp.status_code in (400, 422)


def test_notifications_create_accepts_valid_rule() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "events": ["RUN_FAILED"],
                "template": "Run {{runId}} on {{projectName}} status {{status}}",
                "timeoutSec": 5,
                "maxRetries": 3,
                "provider": "custom-provider",
                "secret": "token",
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["rule"]["events"] == ["RUN_FAILED"]


def test_notifications_create_accepts_canary_rule() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateStrategy": "CANARY",
                "templateName": "run_terminal_summary",
                "templateCanaryVersion": "v2",
                "templateCanaryPercent": 20,
                "autoRollbackEnabled": True,
                "autoRollbackFailureThreshold": 5,
                "autoRollbackWindowMinutes": 60,
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["rule"]["templateStrategy"] == "CANARY"


def test_notifications_create_rejects_canary_missing_version_or_percent() -> None:
    client = TestClient(_build_create_app())
    missing_version = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateStrategy": "CANARY",
                "templateName": "run_terminal_summary",
                "templateCanaryPercent": 20,
            },
            "enabled": True,
        },
    )
    assert missing_version.status_code == 422
    assert "templateCanaryVersion" in missing_version.json()["detail"]

    missing_percent = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateStrategy": "CANARY",
                "templateName": "run_terminal_summary",
                "templateCanaryVersion": "v2",
            },
            "enabled": True,
        },
    )
    assert missing_percent.status_code == 422
    assert "templateCanaryPercent" in missing_percent.json()["detail"]


def test_notifications_create_rejects_canary_percent_out_of_range() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateStrategy": "CANARY",
                "templateCanaryVersion": "v2",
                "templateCanaryPercent": 101,
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "templateCanaryPercent" in resp.json()["detail"]


def test_notifications_create_rejects_auto_rollback_failure_threshold_out_of_range() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "autoRollbackEnabled": True,
                "autoRollbackFailureThreshold": 21,
                "autoRollbackWindowMinutes": 30,
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "autoRollbackFailureThreshold" in resp.json()["detail"]


def test_notifications_create_rejects_template_version_without_name() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {"templateVersion": "v1"},
            "enabled": True,
        },
    )
    assert resp.status_code in (400, 422)


def test_notifications_create_accepts_template_name_and_version() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateName": "run_terminal_summary",
                "templateVersion": "v1",
                "templateScene": "NOTIFICATION_WEBHOOK",
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["rule"]["templateName"] == "run_terminal_summary"
    assert body["data"]["rule"]["templateVersion"] == "v1"


def test_notifications_create_accepts_legacy_template_scene_alias() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateName": "run_terminal_summary",
                "templateVersion": "v1",
                "templateScene": "WEBHOOK",
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["rule"]["templateScene"] == "NOTIFICATION_WEBHOOK"


def test_notifications_create_rejects_invalid_template_scene() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateName": "run_terminal_summary",
                "templateScene": "NOTIFICATION_SMS",
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "templateScene" in resp.json()["detail"]


def test_notifications_create_rejects_template_reference_when_version_not_found() -> None:
    client = TestClient(_build_create_app(db=_CreateNotificationDb(prompt_templates=[])))
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateName": "run_terminal_summary",
                "templateVersion": "v1",
                "templateScene": "NOTIFICATION_WEBHOOK",
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "templateName=run_terminal_summary" in resp.json()["detail"]
    assert "templateVersion=v1" in resp.json()["detail"]


def test_notifications_create_accepts_template_name_without_version_when_active_exists() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {"templateName": "run_terminal_summary"},
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rule"]["templateScene"] == "NOTIFICATION_WEBHOOK"


def test_notifications_create_defaults_template_scene_for_email() -> None:
    client = TestClient(
        _build_create_app(
            db=_CreateNotificationDb(
                prompt_templates=[
                    _default_prompt_template(
                        name="run_terminal_summary",
                        version="v1",
                        is_active=True,
                        scene="NOTIFICATION_EMAIL",
                    )
                ]
            )
        )
    )
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "EMAIL",
            "target": "ops@example.com",
            "rule": {"templateName": "run_terminal_summary"},
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rule"]["templateScene"] == "NOTIFICATION_EMAIL"


def test_notifications_create_defaults_template_scene_for_im() -> None:
    client = TestClient(
        _build_create_app(
            db=_CreateNotificationDb(
                prompt_templates=[
                    _default_prompt_template(
                        name="run_terminal_summary",
                        version="v1",
                        is_active=True,
                        scene="NOTIFICATION_IM",
                    )
                ]
            )
        )
    )
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "IM",
            "target": "im://ops-room",
            "rule": {"templateName": "run_terminal_summary"},
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rule"]["templateScene"] == "NOTIFICATION_IM"


def test_notifications_create_rejects_canary_without_template_name() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateStrategy": "CANARY",
                "templateCanaryVersion": "v2",
                "templateCanaryPercent": 20,
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "templateName" in resp.json()["detail"]


def test_notifications_create_rejects_canary_with_template_version() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateStrategy": "CANARY",
                "templateName": "run_terminal_summary",
                "templateVersion": "v1",
                "templateCanaryVersion": "v2",
                "templateCanaryPercent": 20,
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "templateVersion" in resp.json()["detail"]


def test_notifications_create_rejects_auto_rollback_window_minutes_out_of_range() -> None:
    client = TestClient(_build_create_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "autoRollbackEnabled": True,
                "autoRollbackFailureThreshold": 3,
                "autoRollbackWindowMinutes": 1441,
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "autoRollbackWindowMinutes" in resp.json()["detail"]


def test_notifications_create_rejects_template_reference_when_no_active_template() -> None:
    client = TestClient(
        _build_create_app(
            db=_CreateNotificationDb(
                prompt_templates=[_default_prompt_template(name="run_terminal_summary", version="v1", is_active=False)]
            )
        )
    )
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {"templateName": "run_terminal_summary"},
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "active prompt template" in resp.json()["detail"].lower()


def test_notifications_update_rejects_template_reference_when_not_found() -> None:
    client = TestClient(_build_update_app(db=_UpdateNotificationDb(prompt_templates=[])))
    resp = client.put(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications/"
        "33333333-3333-3333-3333-333333333333",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateName": "run_terminal_summary",
                "templateVersion": "v1",
                "templateScene": "NOTIFICATION_WEBHOOK",
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 422
    assert "templateName=run_terminal_summary" in resp.json()["detail"]


def test_notifications_update_accepts_template_reference_when_exists() -> None:
    client = TestClient(_build_update_app())
    resp = client.put(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications/"
        "33333333-3333-3333-3333-333333333333",
        json={
            "channel": "WEBHOOK",
            "target": "https://hooks.example.com/notify",
            "rule": {
                "templateName": "run_terminal_summary",
                "templateVersion": "v1",
                "templateScene": "NOTIFICATION_WEBHOOK",
            },
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rule"]["templateVersion"] == "v1"


def test_notification_deliveries_list_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    run_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    delivery_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    async def _fake_list_deliveries(
        db,
        *,
        user,
        project_id,
        status,
        run_id,
        page,
        page_size,
    ):
        assert status == "FAILED"
        assert run_id == uuid.UUID("44444444-4444-4444-4444-444444444444")
        assert page == 2
        assert page_size == 5
        return NotificationDeliveryListData(
            page=2,
            pageSize=5,
            total=1,
            items=[
                NotificationDeliveryListItem(
                    id=str(delivery_id),
                    projectId=str(project_id),
                    runId=str(run_id),
                    notificationId=str(uuid.UUID("66666666-6666-6666-6666-666666666666")),
                    channel="WEBHOOK",
                    target="https://hooks.example.com/notify",
                    provider="WEBHOOK",
                    status="FAILED",
                    attempts=3,
                    maxRetries=3,
                    nextRetryAt=None,
                    lastError="HTTP 500",
                    lastStatusCode=500,
                    lastDurationMs=80,
                    createdAt=1710000000,
                    updatedAt=1710000010,
                )
            ],
        )

    monkeypatch.setattr(integrations_endpoint, "list_notification_deliveries", _fake_list_deliveries)
    client = TestClient(_build_app())
    resp = client.get(
        f"/api/projects/{project_id}/integrations/notifications/deliveries",
        params={"status": "FAILED", "runId": str(run_id), "page": 2, "pageSize": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["id"] == str(delivery_id)


def test_notification_diagnostics_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    notification_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_diagnostics(db, *, user, project_id):
        return NotificationDiagnosticsData(
            summary=NotificationDiagnosticsSummary(
                status="WARN",
                total=2,
                blocking=0,
                warnings=2,
                ready=0,
                failedDeliveries=1,
            ),
            checks=[
                NotificationDiagnosticsCheck(
                    id="rule_disabled",
                    level="WARNING",
                    scope="rule",
                    title="Rule is disabled",
                    detail="Notification rule is disabled.",
                    recommendation="Enable the rule.",
                    notificationId=str(notification_id),
                ),
                NotificationDiagnosticsCheck(
                    id="recent_failed_deliveries",
                    level="WARNING",
                    scope="delivery",
                    title="Recent failed deliveries found",
                    detail="1 failed delivery records exist.",
                    recommendation="Inspect and retry.",
                    notificationId=None,
                ),
            ],
            recentFailures=[
                NotificationDiagnosticsFailure(
                    id="55555555-5555-5555-5555-555555555555",
                    notificationId=str(notification_id),
                    channel="WEBHOOK",
                    target="https://hooks.example.com/notify",
                    provider="WEBHOOK",
                    status="FAILED",
                    attempts=2,
                    lastStatusCode=500,
                    lastError="HTTP 500",
                    updatedAt=1710000010,
                )
            ],
            providerReadiness=[
                NotificationDiagnosticsProviderReadiness(
                    provider="WEBHOOK",
                    ready=True,
                    reason="Provider is supported and configured.",
                    notificationCount=1,
                )
            ],
        )

    monkeypatch.setattr(integrations_endpoint, "get_notification_diagnostics", _fake_diagnostics)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/integrations/notifications/diagnostics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["summary"]["status"] == "WARN"
    assert body["data"]["summary"]["failedDeliveries"] == 1
    assert len(body["data"]["checks"]) == 2
    assert body["data"]["recentFailures"][0]["status"] == "FAILED"
    assert body["data"]["providerReadiness"][0]["provider"] == "WEBHOOK"


def test_notification_delivery_retry_rejects_invalid_status(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_retry(db, *, user, project_id, delivery_id):
        raise HTTPException(status_code=400, detail="Only FAILED/QUEUED delivery can be retried")

    monkeypatch.setattr(integrations_endpoint, "retry_notification_delivery", _fake_retry)
    client = TestClient(_build_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/integrations/notifications/deliveries/"
        "77777777-7777-7777-7777-777777777777/retry"
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Only FAILED/QUEUED delivery can be retried"


class _RetryDeliveryDb:
    def __init__(self) -> None:
        self._project = Project(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            name="proj",
            owner_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        )
        self._delivery = NotificationOutbox(
            id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
            tenant_id=self._project.tenant_id,
            project_id=self._project.id,
            run_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
            notification_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            channel="WEBHOOK",
            target="https://hooks.example.com/notify",
            provider="WEBHOOK",
            payload_json={"runId": "44444444-4444-4444-4444-444444444444"},
            rule_json={},
            status="FAILED",
            attempts=1,
            max_retries=3,
            next_retry_at=None,
        )

    async def scalar(self, stmt):
        text = str(stmt)
        if "FROM projects" in text:
            return self._project
        if "FROM notification_outbox" in text:
            return self._delivery
        return None

    async def execute(self, stmt):
        text = str(stmt)
        if "project_members.role" in text:
            return _ScalarResult(ProjectRole.EDITOR)
        return _ScalarResult(None)

    async def flush(self) -> None:
        return None


def test_retry_notification_delivery_triggers_immediate_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    async def _fake_process_outbox_item(db, *, outbox, retry_base_seconds=5):
        called["value"] = True
        outbox.status = "SENT"
        outbox.attempts = int(outbox.attempts or 0) + 1
        outbox.next_retry_at = None

    monkeypatch.setattr(integration_config, "process_notification_outbox_item", _fake_process_outbox_item)
    db = _RetryDeliveryDb()
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset(),
    )
    result = anyio.run(
        lambda: integration_config.retry_notification_delivery(
            db,
            user=user,
            project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            delivery_id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        )
    )
    assert called["value"] is True
    assert result.status == "SENT"
    assert result.attempts == 2


def test_notification_strategy_center_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    notification_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_strategy_center(db, *, user, project_id):
        return [
            NotificationStrategyCenterItem(
                id=str(notification_id),
                channel="WEBHOOK",
                target="https://hooks.example.com/notify",
                enabled=True,
                events=["RUN_FAILED", "RUN_FINISHED"],
                templateStrategySummary={"mode": "CANARY", "templateName": "run_terminal_summary"},
                rolloutScopeSummary={
                    "envIdsCount": 1,
                    "triggerTypes": ["CI"],
                    "metaTagsCount": 1,
                    "batchPercent": 50,
                    "timeWindows": {"total": 0, "enabled": 0, "conflictStrategy": "priority_asc_then_weight_desc_then_array_order"},
                },
                autoRollbackSummary={"enabled": True, "failureThreshold": 3, "windowMinutes": 60},
                deliveryStats=NotificationStrategyCenterDeliveryStats(
                    sent=9,
                    failed=1,
                    queued=2,
                    lastDeliveryAt=1710000030,
                    lastStatus="FAILED",
                ),
                filterReasonStats=NotificationStrategyCenterFilterReasonStats(
                    scopeReason=3,
                    eventFiltered=2,
                    unsupportedProvider=1,
                    templateNotFound=1,
                ),
            )
        ]

    monkeypatch.setattr(integrations_endpoint, "list_notification_strategy_center", _fake_strategy_center)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/integrations/notifications/strategy-center")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == str(notification_id)
    assert body["data"][0]["deliveryStats"]["sent"] == 9
    assert body["data"][0]["filterReasonStats"]["scopeReason"] == 3
    assert body["data"][0]["rolloutScopeSummary"]["timeWindows"]["total"] == 0


def test_notification_strategy_center_simulate_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    notification_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_simulate(db, *, user, project_id, notification_id, run_context):
        assert run_context["triggerType"] == "MANUAL"
        return integration_config.NotificationStrategySimulationResult(
            matched=True,
            scopeReason="ok",
            scopeDecision={"selectedWindowId": "w2", "matchedWindowCount": 2, "reason": "window_selected_by_priority_weight_order"},
            resolvedBatchPercent=20,
            resolvedPriority=10,
            resolvedLayer={"layerKey": "releaseRing", "layerValue": "canary"},
            resolvedTimeWindow={"id": "w2", "priority": 10, "weight": 80},
            explanations=["env matched", "selected timeWindow w2 by priority/weight"],
            conflictCandidates=[{"id": "w1", "priority": 10, "weight": 20}, {"id": "w2", "priority": 10, "weight": 80}],
        )

    monkeypatch.setattr(integrations_endpoint, "simulate_notification_strategy", _fake_simulate)
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/integrations/notifications/strategy-center/simulate",
        json={
            "notificationId": str(notification_id),
            "runContext": {
                "triggerType": "MANUAL",
                "metaTags": ["smoke"],
                "weekday": 5,
                "hour": 10,
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["matched"] is True
    assert body["data"]["scopeReason"] == "ok"
    assert body["data"]["scopeDecision"]["selectedWindowId"] == "w2"
    assert body["data"]["resolvedBatchPercent"] == 20
    assert body["data"]["explanations"][0] == "env matched"
    assert len(body["data"]["conflictCandidates"]) == 2


def test_notification_strategy_center_simulate_batch_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    notification_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_simulate_batch(db, *, user, project_id, notification_id, run_contexts):
        assert len(run_contexts) == 2
        assert run_contexts[0].triggerType == "MANUAL"
        return integration_config.NotificationStrategySimulationBatchResult(
            items=[
                integration_config.NotificationStrategySimulationBatchItem(
                    runContext=run_contexts[0],
                    result=integration_config.NotificationStrategySimulationResult(
                        matched=True,
                        scopeReason="ok",
                        scopeDecision={"selectedWindowId": "w2"},
                        resolvedBatchPercent=20,
                        resolvedPriority=10,
                        resolvedLayer={},
                        resolvedTimeWindow={"id": "w2"},
                        explanations=["env matched"],
                        conflictCandidates=[],
                    ),
                ),
                integration_config.NotificationStrategySimulationBatchItem(
                    runContext=run_contexts[1],
                    result=integration_config.NotificationStrategySimulationResult(
                        matched=False,
                        scopeReason="scope_trigger_filtered",
                        scopeDecision={},
                        resolvedBatchPercent=None,
                        resolvedPriority=10,
                        resolvedLayer={},
                        resolvedTimeWindow={},
                        explanations=["trigger filtered"],
                        conflictCandidates=[],
                    ),
                ),
            ]
        )

    monkeypatch.setattr(integrations_endpoint, "simulate_notification_strategy_batch", _fake_simulate_batch)
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/integrations/notifications/strategy-center/simulate-batch",
        json={
            "notificationId": str(notification_id),
            "runContexts": [
                {"triggerType": "MANUAL", "weekday": 5, "hour": 10},
                {"triggerType": "CI", "weekday": 5, "hour": 10},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert len(body["data"]["items"]) == 2
    assert body["data"]["items"][0]["runContext"]["triggerType"] == "MANUAL"
    assert body["data"]["items"][1]["result"]["scopeReason"] == "scope_trigger_filtered"


def test_notification_strategy_center_simulate_batch_rejects_empty_run_contexts() -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    notification_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/integrations/notifications/strategy-center/simulate-batch",
        json={"notificationId": str(notification_id), "runContexts": []},
    )
    assert resp.status_code == 422


def test_notification_strategy_center_simulate_batch_rejects_invalid_notification_id() -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/integrations/notifications/strategy-center/simulate-batch",
        json={"notificationId": "bad-id", "runContexts": [{"triggerType": "MANUAL"}]},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "notificationId must be a UUID"


def test_list_notification_strategy_center_time_windows_summary() -> None:
    now = datetime.now(UTC)
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    notification_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    class _StrategyDb:
        def __init__(self) -> None:
            self._project = Project(
                id=project_id,
                tenant_id=tenant_id,
                name="proj",
                owner_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            )
            self._notification = Notification(
                id=notification_id,
                tenant_id=tenant_id,
                project_id=project_id,
                channel="WEBHOOK",
                target="https://hooks.example.com/notify",
                rule_json={
                    "events": ["RUN_FAILED"],
                    "rolloutScope": {
                        "timeWindows": [
                            {
                                "id": "w1",
                                "enabled": True,
                                "priority": 10,
                                "weight": 50,
                                "timeWindow": {"weekdays": [1, 2, 3], "startHour": 9, "endHour": 18},
                            },
                            {
                                "id": "w2",
                                "enabled": False,
                                "priority": 20,
                                "weight": 30,
                                "timeWindow": {"weekdays": [6, 7]},
                            },
                        ]
                    },
                },
                enabled=True,
                created_at=now,
            )

        async def scalar(self, stmt):
            if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Project:
                return self._project
            return None

        async def execute(self, stmt):
            sql = str(stmt)
            if "FROM notifications" in sql:
                return _ScalarsResult([self._notification])
            if "FROM notification_outbox" in sql:
                return _ScalarsResult([])
            if "FROM runs" in sql:
                return _RowsResult(
                    [
                        (
                            {
                                "notificationDispatch": {
                                    "terminal": {
                                        "results": [
                                            {
                                                "notificationId": str(notification_id),
                                                "reason": "ok",
                                            },
                                            {
                                                "notificationId": str(notification_id),
                                                "reason": "scope_filtered",
                                            },
                                            {
                                                "notificationId": str(notification_id),
                                                "reason": "event_filtered",
                                            },
                                            {
                                                "notificationId": str(notification_id),
                                                "reason": "scope_trigger_filtered",
                                            },
                                            {
                                                "notificationId": str(notification_id),
                                                "reason": "unsupported_provider",
                                            },
                                            {
                                                "notificationId": str(uuid.uuid4()),
                                                "reason": "ok",
                                            },
                                        ]
                                    }
                                }
                            },
                        )
                    ]
                )
            if "project_members.role" in sql:
                return _ScalarResult(ProjectRole.EDITOR)
            return _RowsResult([])

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=tenant_id,
        roles=frozenset(),
    )
    items = anyio.run(
        lambda: integration_config.list_notification_strategy_center(
            _StrategyDb(),
            user=user,
            project_id=project_id,
        )
    )
    assert len(items) == 1
    summary = items[0].rolloutScopeSummary["timeWindows"]
    assert summary["total"] == 2
    assert summary["enabled"] == 1
    assert summary["conflictStrategy"] == "priority_asc_then_weight_desc_then_array_order"
    simulation_stats = items[0].simulationStats
    assert simulation_stats is not None
    assert simulation_stats.sampleCount == 5
    assert simulation_stats.matchedCount == 3
    assert [item.model_dump() for item in simulation_stats.scopeReasonTop] == [
        {"reason": "scope_filtered", "count": 1},
        {"reason": "scope_trigger_filtered", "count": 1},
    ]


def test_notification_diagnostics_no_rules_blocked() -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    class _DiagnosticsDb:
        def __init__(self) -> None:
            self._project = Project(
                id=project_id,
                tenant_id=tenant_id,
                name="proj",
                owner_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            )

        async def scalar(self, stmt):
            if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Project:
                return self._project
            return None

        async def execute(self, stmt):
            sql = str(stmt)
            if "FROM notifications" in sql:
                return _ScalarsResult([])
            if "FROM notification_outbox" in sql:
                return _ScalarsResult([])
            if "project_members.role" in sql:
                return _ScalarResult(ProjectRole.EDITOR)
            return _RowsResult([])

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=tenant_id,
        roles=frozenset(),
    )
    data = anyio.run(
        lambda: integration_config.get_notification_diagnostics(
            _DiagnosticsDb(),
            user=user,
            project_id=project_id,
        )
    )
    assert data.summary.status == "BLOCKED"
    assert data.summary.blocking == 1
    assert len(data.checks) == 1
    assert data.checks[0].id == "no_rules"


def test_notification_diagnostics_mixed_rules_failures_and_template_missing() -> None:
    now = datetime.now(UTC)
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    n1_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    n2_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    class _DiagnosticsDb:
        def __init__(self) -> None:
            self._project = Project(
                id=project_id,
                tenant_id=tenant_id,
                name="proj",
                owner_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            )
            self._notifications = [
                Notification(
                    id=n1_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    channel="WEBHOOK",
                    target="https://hooks.example.com/notify",
                    rule_json={
                        "provider": "WEBHOOK",
                        "events": ["RUN_FAILED"],
                        "templateName": "missing_template",
                    },
                    enabled=True,
                    created_at=now,
                ),
                Notification(
                    id=n2_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    channel="SMS",
                    target="",
                    rule_json={
                        "provider": "SMS",
                        "events": [],
                    },
                    enabled=False,
                    created_at=now,
                ),
            ]
            self._outbox = [
                NotificationOutbox(
                    id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
                    tenant_id=tenant_id,
                    project_id=project_id,
                    run_id=uuid.UUID("66666666-6666-6666-6666-666666666666"),
                    notification_id=n1_id,
                    channel="WEBHOOK",
                    target="https://hooks.example.com/notify",
                    provider="WEBHOOK",
                    payload_json={},
                    rule_json={},
                    status="FAILED",
                    attempts=2,
                    max_retries=3,
                    last_status_code=500,
                    last_error="HTTP 500",
                    updated_at=now,
                )
            ]

        async def scalar(self, stmt):
            if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is Project:
                return self._project
            if stmt.column_descriptions and stmt.column_descriptions[0].get("entity") is PromptTemplate:
                return None
            return None

        async def execute(self, stmt):
            sql = str(stmt)
            if "FROM notifications" in sql:
                return _ScalarsResult(self._notifications)
            if "FROM notification_outbox" in sql:
                return _ScalarsResult(self._outbox)
            if "project_members.role" in sql:
                return _ScalarResult(ProjectRole.EDITOR)
            return _RowsResult([])

    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=tenant_id,
        roles=frozenset(),
    )
    data = anyio.run(
        lambda: integration_config.get_notification_diagnostics(
            _DiagnosticsDb(),
            user=user,
            project_id=project_id,
        )
    )
    assert data.summary.status == "BLOCKED"
    assert data.summary.blocking >= 3
    assert data.summary.warnings >= 2
    assert data.summary.failedDeliveries == 1
    assert len(data.recentFailures) == 1
    assert data.recentFailures[0].status == "FAILED"
    check_ids = {item.id for item in data.checks}
    assert f"{n1_id}:template_missing" in check_ids
    assert f"{n2_id}:provider_unsupported" in check_ids
    assert f"{n2_id}:events_missing" in check_ids
    assert "recent_failed_deliveries" in check_ids
    providers = {item.provider: item for item in data.providerReadiness}
    assert providers["WEBHOOK"].ready is False
    assert "TEMPLATE_MISSING" in providers["WEBHOOK"].reason
    assert "WEBHOOK_SECRET_MISSING" in providers["WEBHOOK"].reason
    assert "RECENT_FAILED_DELIVERY" in providers["WEBHOOK"].reason
    assert providers["SMS"].ready is False


def test_notification_audit_log_called_on_create_update_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    async def _fake_create_audit_log(db, **kwargs):
        calls.append(kwargs)
        return None

    monkeypatch.setattr(integration_config, "create_audit_log", _fake_create_audit_log)
    db = _UpdateNotificationDb(
        notification=_build_existing_notification(),
        prompt_templates=[_default_prompt_template(name="run_terminal_summary", version="v1", is_active=True)],
    )
    user = CurrentUser(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        roles=frozenset({"ADMIN"}),
    )
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    notification_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    create_result = anyio.run(
        lambda: integration_config.create_notification_config(
            db,
            user=user,
            project_id=project_id,
            payload=integration_config.NotificationConfigCreateRequest(
                channel="WEBHOOK",
                target="https://hooks.example.com/notify",
                rule={"events": ["RUN_FAILED"]},
                enabled=True,
            ),
        )
    )
    assert create_result.channel == "WEBHOOK"

    update_result = anyio.run(
        lambda: integration_config.update_notification_config(
            db,
            user=user,
            project_id=project_id,
            notification_id=notification_id,
            payload=integration_config.NotificationConfigUpdateRequest(
                channel="EMAIL",
                target="ops@example.com",
                rule={"events": ["RUN_FAILED", "RUN_FINISHED"]},
                enabled=False,
            ),
        )
    )
    assert update_result.channel == "EMAIL"

    anyio.run(
        lambda: integration_config.delete_notification_config(
            db,
            user=user,
            project_id=project_id,
            notification_id=notification_id,
        )
    )

    assert len(calls) == 3
    assert calls[0]["module"] == "INTEGRATION"
    assert calls[0]["action"] == "CREATE_NOTIFICATION_RULE"
    assert calls[0]["detail"]["channel"] == "WEBHOOK"
    assert calls[0]["detail"]["events"] == ["RUN_FAILED"]

    assert calls[1]["module"] == "INTEGRATION"
    assert calls[1]["action"] == "UPDATE_NOTIFICATION_RULE"
    assert calls[1]["detail"]["channel"] == "EMAIL"
    assert calls[1]["detail"]["enabled"] is False

    assert calls[2]["module"] == "INTEGRATION"
    assert calls[2]["action"] == "DELETE_NOTIFICATION_RULE"
    assert calls[2]["detail"]["target"] == "ops@example.com"
