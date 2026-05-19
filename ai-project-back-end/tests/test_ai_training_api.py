from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import ai_training as ai_training_endpoint
from app.core.database import get_db
from app.schemas.ai_training import (
    AiTrainingJobCreateRequest,
    AiTrainingJobDetail,
    AiTrainingJobListItem,
)


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_JOB_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_DATASET_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(
        ai_training_endpoint.router,
        prefix="/api",
    )

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=_USER_ID,
            tenant_id=_TENANT_ID,
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def _make_job_detail(name: str = "Fine-tune model", training_type: str = "FINE_TUNE") -> AiTrainingJobDetail:
    return AiTrainingJobDetail(
        id=str(_JOB_ID),
        projectId=str(_PROJECT_ID),
        name=name,
        description="",
        trainingType=training_type,
        baseModel="deepseek-chat",
        status="DRAFT",
        progress=0.0,
        metrics={},
        datasetConfig={},
        hyperparams={},
        createdBy=str(_USER_ID),
        createdAt=1710000000,
        updatedAt=1710000000,
    )


def test_create_training_job(monkeypatch) -> None:
    async def _fake_create(db, *, user, project_id, payload):
        return _make_job_detail(name=payload.name, training_type=payload.trainingType)

    monkeypatch.setattr(ai_training_endpoint, "create_training_job", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/ai-training/jobs",
        json={
            "name": "Fine-tune model",
            "trainingType": "FINE_TUNE",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Fine-tune model"
    assert body["data"]["trainingType"] == "FINE_TUNE"
    assert body["data"]["baseModel"] == "deepseek-chat"


def test_create_training_job_embedding_type(monkeypatch) -> None:
    async def _fake_create(db, *, user, project_id, payload):
        return _make_job_detail(name=payload.name, training_type=payload.trainingType)

    monkeypatch.setattr(ai_training_endpoint, "create_training_job", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/ai-training/jobs",
        json={
            "name": "Embedding model",
            "trainingType": "EMBEDDING",
            "baseModel": "deepseek-coder",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Embedding model"
    assert body["data"]["trainingType"] == "EMBEDDING"


def test_list_training_jobs_empty(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id, page, page_size, status=None):
        return (0, [])

    monkeypatch.setattr(ai_training_endpoint, "list_training_jobs", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/ai-training/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_list_training_jobs_with_data(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id, page, page_size, status=None):
        item = AiTrainingJobListItem(
            id=str(_JOB_ID),
            projectId=str(_PROJECT_ID),
            name="Fine-tune model",
            description="",
            trainingType="FINE_TUNE",
            baseModel="deepseek-chat",
            status="DRAFT",
            progress=0.0,
            metrics={},
            createdBy=str(_USER_ID),
            createdAt=1710000000,
            updatedAt=1710000000,
        )
        return (1, [item])

    monkeypatch.setattr(ai_training_endpoint, "list_training_jobs", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/ai-training/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "Fine-tune model"


def test_get_training_job(monkeypatch) -> None:
    async def _fake_get(db, *, user, project_id, job_id):
        return _make_job_detail()

    monkeypatch.setattr(ai_training_endpoint, "get_training_job", _fake_get)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/ai-training/jobs/{_JOB_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["id"] == str(_JOB_ID)


def test_update_training_job(monkeypatch) -> None:
    async def _fake_update(db, *, user, project_id, job_id, payload):
        return _make_job_detail(name=payload.name or "Updated")

    monkeypatch.setattr(ai_training_endpoint, "update_training_job", _fake_update)

    client = TestClient(_build_app())
    resp = client.put(
        f"/api/projects/{_PROJECT_ID}/ai-training/jobs/{_JOB_ID}",
        json={"name": "Updated Job"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Updated Job"


def test_delete_training_job(monkeypatch) -> None:
    async def _fake_delete(db, *, user, project_id, job_id):
        return None

    monkeypatch.setattr(ai_training_endpoint, "delete_training_job", _fake_delete)

    client = TestClient(_build_app())
    resp = client.delete(f"/api/projects/{_PROJECT_ID}/ai-training/jobs/{_JOB_ID}")
    assert resp.status_code == 200


def test_start_training(monkeypatch) -> None:
    async def _fake_start(db, *, user, project_id, job_id):
        detail = _make_job_detail()
        detail.status = "TRAINING"
        detail.progress = 0.0
        return detail

    monkeypatch.setattr(ai_training_endpoint, "start_training", _fake_start)

    client = TestClient(_build_app())
    resp = client.post(f"/api/projects/{_PROJECT_ID}/ai-training/jobs/{_JOB_ID}/start")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "TRAINING"


def test_get_training_progress(monkeypatch) -> None:
    from app.schemas.ai_training import AiTrainingJobProgress

    async def _fake_progress(db, *, user, project_id, job_id):
        return AiTrainingJobProgress(
            status="TRAINING",
            progress=0.5,
            metrics={"loss": 0.35},
        )

    monkeypatch.setattr(ai_training_endpoint, "get_training_progress", _fake_progress)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/ai-training/jobs/{_JOB_ID}/progress")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "TRAINING"
    assert body["data"]["progress"] == 0.5
    assert body["data"]["metrics"]["loss"] == 0.35


def test_create_dataset(monkeypatch) -> None:
    from app.schemas.ai_training import AiTrainingDatasetListItem

    async def _fake_create(db, *, user, project_id, payload):
        return AiTrainingDatasetListItem(
            id=str(_DATASET_ID),
            projectId=str(_PROJECT_ID),
            name=payload.name,
            sourceType=payload.sourceType,
            recordCount=0,
        )

    monkeypatch.setattr(ai_training_endpoint, "create_dataset", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/ai-training/datasets",
        json={"name": "Test Dataset", "sourceType": "TESTCASES"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Test Dataset"
    assert body["data"]["sourceType"] == "TESTCASES"


def test_list_datasets_empty(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id, page, page_size):
        return (0, [])

    monkeypatch.setattr(ai_training_endpoint, "list_datasets", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/ai-training/datasets")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0
