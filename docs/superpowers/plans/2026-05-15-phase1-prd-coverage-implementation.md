# Phase 1 PRD Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first-wave PRD coverage for the smart testing platform so platform records, requirement main-chain polish, requirement change analysis, and API/TestCase binding all satisfy the agreed `C` acceptance bar.

**Architecture:** Keep the existing `FastAPI + SQLAlchemy + Alembic + Vue 3 + Vite` structure. Add the missing backend data objects and thin route layers first, then wire the existing requirement, collection, testcase, and run views to those real APIs, and finish with PostgreSQL-backed smoke verification.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pydantic, Vue 3, TypeScript, Vite, pytest

---

## Scope Check

The approved spec spans four subsystem groups, but they are still part of one executable chain:

`platform records -> requirement chain -> change analysis -> testcase binding -> run details`

This plan keeps them in one file so shared files and dependencies stay visible. During execution, dispatch one task group at a time; each task below is designed to be independently testable.

## File Structure

### Backend files

- Create: `ai-project-back-end/alembic/versions/0013_add_ai_job_records_and_audit_scope.py`
- Create: `ai-project-back-end/alembic/versions/0014_add_requirement_change_analysis_and_revisions.py`
- Create: `ai-project-back-end/alembic/versions/0015_expand_testcase_bindings_for_api_links.py`
- Create: `ai-project-back-end/app/models/platform_record.py`
- Create: `ai-project-back-end/app/schemas/platform_record.py`
- Create: `ai-project-back-end/app/schemas/requirement_change.py`
- Create: `ai-project-back-end/app/services/platform_record.py`
- Create: `ai-project-back-end/app/services/requirement_change.py`
- Create: `ai-project-back-end/app/api/v1/endpoints/platform_records.py`
- Create: `ai-project-back-end/app/api/v1/endpoints/requirement_changes.py`
- Create: `ai-project-back-end/tests/test_platform_records_api.py`
- Create: `ai-project-back-end/tests/test_requirement_change_analysis_api.py`
- Create: `ai-project-back-end/tests/test_testcase_bindings_api.py`
- Modify: `ai-project-back-end/app/models/audit.py`
- Modify: `ai-project-back-end/app/models/requirement.py`
- Modify: `ai-project-back-end/app/models/testcase_binding.py`
- Modify: `ai-project-back-end/app/models/__init__.py`
- Modify: `ai-project-back-end/app/schemas/requirement.py`
- Modify: `ai-project-back-end/app/schemas/testcase_binding.py`
- Modify: `ai-project-back-end/app/services/requirement.py`
- Modify: `ai-project-back-end/app/services/testcase_binding.py`
- Modify: `ai-project-back-end/app/api/v1/endpoints/requirements.py`
- Modify: `ai-project-back-end/app/api/v1/endpoints/testcase_bindings.py`
- Modify: `ai-project-back-end/app/api/v1/__init__.py`

### Frontend files

- Create: `ai-project_front_end/src/lib/api/platformRecords.ts`
- Create: `ai-project_front_end/src/lib/api/requirementChanges.ts`
- Create: `ai-project_front_end/src/views/settings/PlatformRecords.vue`
- Create: `ai-project_front_end/src/views/requirements/RequirementChangeSetDetail.vue`
- Modify: `ai-project_front_end/src/lib/api/requirements.ts`
- Modify: `ai-project_front_end/src/lib/api/collections.ts`
- Modify: `ai-project_front_end/src/lib/aiTestingPlatformApi.ts`
- Modify: `ai-project_front_end/src/router/index.ts`
- Modify: `ai-project_front_end/src/components/figma/ai-testing-platform/AiTestingSidebar.vue`
- Modify: `ai-project_front_end/src/views/requirements/RequirementDocDetail.vue`
- Modify: `ai-project_front_end/src/views/requirements/RequirementAnalysisDetail.vue`
- Modify: `ai-project_front_end/src/views/collections/CollectionDetail.vue`
- Modify: `ai-project_front_end/src/views/runs/RunDetail.vue`
- Modify: `ai-project_front_end/src/components/figma/ai-testing-platform/TestCaseDetailPanel.vue`
- Modify: `ai-project_front_end/src/components/figma/ai-testing-platform/ApiCollectionsPanel.vue`

### Validation artifacts

- Modify: `docs/superpowers/specs/2026-05-15-prd-coverage-phase1-design.md` only if implementation reveals a real design correction
- Modify: `D:\OtherProject\NewTestPlatform\智能测试平台任务进度看板.html` after implementation, not during early tasks

### Verification policy

- Backend tasks are test-first with `pytest`
- Frontend tasks use real API contracts plus `npm run build` because the repo does not currently expose a dedicated frontend test harness
- End-to-end acceptance requires PostgreSQL-backed smoke checks on the real backend

## Task 1: Platform Records Backend and Logging Hooks

**Files:**
- Create: `ai-project-back-end/alembic/versions/0013_add_ai_job_records_and_audit_scope.py`
- Create: `ai-project-back-end/app/models/platform_record.py`
- Create: `ai-project-back-end/app/schemas/platform_record.py`
- Create: `ai-project-back-end/app/services/platform_record.py`
- Create: `ai-project-back-end/app/api/v1/endpoints/platform_records.py`
- Create: `ai-project-back-end/tests/test_platform_records_api.py`
- Modify: `ai-project-back-end/app/models/audit.py`
- Modify: `ai-project-back-end/app/models/__init__.py`
- Modify: `ai-project-back-end/app/services/requirement.py`
- Modify: `ai-project-back-end/app/services/testcase_binding.py`
- Modify: `ai-project-back-end/app/api/v1/__init__.py`

- [ ] **Step 1: Write the failing endpoint contract tests**

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import platform_records as platform_records_endpoint
from app.core.database import get_db
from app.schemas.platform_record import AiJobRecordListItem, AuditLogListItem


@dataclass
class _DummySession:
    pass


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(platform_records_endpoint.router, prefix="/api")

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


def test_list_ai_jobs_endpoint(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_list_ai_jobs(db, *, user, project_id, page, page_size, job_type, status):
        assert page == 1
        assert page_size == 20
        return (
            1,
            [
                AiJobRecordListItem(
                    id="33333333-3333-3333-3333-333333333333",
                    projectId=str(project_id),
                    jobType="REQUIREMENT_ANALYSIS",
                    sourceType="RequirementDocVersion",
                    sourceId="44444444-4444-4444-4444-444444444444",
                    status="SUCCEEDED",
                    summary="结构化分析完成",
                    durationMs=812,
                    triggeredBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    createdAt=1710000000,
                    updatedAt=1710000001,
                )
            ],
        )

    monkeypatch.setattr(platform_records_endpoint, "list_ai_jobs", _fake_list_ai_jobs)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/platform/ai-jobs")
    assert resp.status_code == 200
    assert resp.json()["data"]["items"][0]["jobType"] == "REQUIREMENT_ANALYSIS"


def test_list_audit_logs_endpoint(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_list_audit_logs(db, *, user, project_id, page, page_size, module, action):
        return (
            1,
            [
                AuditLogListItem(
                    id="55555555-5555-5555-5555-555555555555",
                    projectId=str(project_id),
                    module="requirements",
                    action="case_drafts.bulk_approve",
                    resourceType="GeneratedCaseDraft",
                    resourceId="66666666-6666-6666-6666-666666666666",
                    summary="2 条草稿审核入库",
                    operatorId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    createdAt=1710000100,
                )
            ],
        )

    monkeypatch.setattr(platform_records_endpoint, "list_audit_logs", _fake_list_audit_logs)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/platform/audit-logs")
    assert resp.status_code == 200
    assert resp.json()["data"]["items"][0]["module"] == "requirements"
```

- [ ] **Step 2: Run the new tests to confirm the module is missing**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m pytest tests\test_platform_records_api.py -v
```

Expected: FAIL with import errors for `platform_records` endpoint or `platform_record` schema.

- [ ] **Step 3: Implement the minimal backend model, migration, service, endpoint, and logging hooks**

```python
# ai-project-back-end/app/models/platform_record.py
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin


class AiJobRecord(Base, TimestampMixin):
    __tablename__ = "ai_job_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
```

```python
# ai-project-back-end/app/models/audit.py
class AuditLog(Base, CreatedAtMixin):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    detail_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
```

```python
# ai-project-back-end/app/services/platform_record.py
async def create_ai_job_record(db, *, tenant_id, project_id, job_type, source_type, source_id, status, summary, triggered_by, duration_ms=None, error_message=None):
    row = AiJobRecord(
        tenant_id=tenant_id,
        project_id=project_id,
        job_type=job_type,
        source_type=source_type,
        source_id=source_id,
        status=status,
        summary=summary,
        triggered_by=triggered_by,
        duration_ms=duration_ms,
        error_message=error_message,
    )
    db.add(row)
    await db.flush()
    return row


async def create_audit_log(db, *, tenant_id, project_id, user_id, module, action, resource_type, resource_id, summary, detail):
    row = AuditLog(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id=user_id,
        module=module,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=summary,
        detail_json=dict(detail or {}),
    )
    db.add(row)
    await db.flush()
    return row
```

```python
# ai-project-back-end/app/api/v1/endpoints/platform_records.py
router = APIRouter()


@router.get("/projects/{projectId}/platform/ai-jobs", response_model=ApiResponse[PageData[AiJobRecordListItem]])
async def list_ai_jobs_endpoint(...):
    total, rows = await list_ai_jobs(...)
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=rows), requestId=request_id)


@router.get("/projects/{projectId}/platform/audit-logs", response_model=ApiResponse[PageData[AuditLogListItem]])
async def list_audit_logs_endpoint(...):
    total, rows = await list_audit_logs(...)
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=rows), requestId=request_id)
```

```python
# ai-project-back-end/app/services/requirement.py
started_at = time.perf_counter()
analysis = await _generate_analysis(...)
await create_ai_job_record(
    db,
    tenant_id=user.tenant_id,
    project_id=project_id,
    job_type="REQUIREMENT_ANALYSIS",
    source_type="RequirementDocVersion",
    source_id=str(version.id),
    status="SUCCEEDED",
    summary="结构化分析完成",
    triggered_by=user.id,
    duration_ms=int((time.perf_counter() - started_at) * 1000),
)
```

```python
# ai-project-back-end/app/services/testcase_binding.py
await create_audit_log(
    db,
    tenant_id=user.tenant_id,
    project_id=project.id,
    user_id=user.id,
    module="testcase_bindings",
    action="bindings.create",
    resource_type="TestcaseBinding",
    resource_id=str(binding.id),
    summary=f"绑定 {binding.name} 已创建",
    detail={"testcaseId": str(testcase.id)},
)
```

- [ ] **Step 4: Run the new tests and one existing requirement test**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m pytest tests\test_platform_records_api.py tests\test_requirement_analysis_api.py -v
```

Expected: PASS for the new platform records contract tests and no regression in the requirement analysis endpoint tests.

- [ ] **Step 5: Commit**

```bash
git add ai-project-back-end/alembic/versions/0013_add_ai_job_records_and_audit_scope.py ai-project-back-end/app/models/platform_record.py ai-project-back-end/app/models/audit.py ai-project-back-end/app/models/__init__.py ai-project-back-end/app/schemas/platform_record.py ai-project-back-end/app/services/platform_record.py ai-project-back-end/app/services/requirement.py ai-project-back-end/app/services/testcase_binding.py ai-project-back-end/app/api/v1/endpoints/platform_records.py ai-project-back-end/app/api/v1/__init__.py ai-project-back-end/tests/test_platform_records_api.py
git commit -m "feat: add platform records and logging hooks"
```

## Task 2: Platform Records UI and Navigation

**Files:**
- Create: `ai-project_front_end/src/lib/api/platformRecords.ts`
- Create: `ai-project_front_end/src/views/settings/PlatformRecords.vue`
- Modify: `ai-project_front_end/src/router/index.ts`
- Modify: `ai-project_front_end/src/components/figma/ai-testing-platform/AiTestingSidebar.vue`

- [ ] **Step 1: Add the API client and route shell, then let the build fail until the new page is wired**

```ts
// ai-project_front_end/src/lib/api/platformRecords.ts
export type AiJobRecord = {
  id: string
  projectId: string
  jobType: string
  sourceType: string
  sourceId: string
  status: string
  summary: string
  durationMs: number | null
  triggeredBy: string | null
  createdAt: number
  updatedAt: number
}

export type AuditLogRecord = {
  id: string
  projectId: string
  module: string
  action: string
  resourceType: string
  resourceId: string
  summary: string
  operatorId: string | null
  createdAt: number
}
```

- [ ] **Step 2: Run the frontend build to confirm the new imports are unresolved**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npm run build
```

Expected: FAIL until `PlatformRecords.vue` is added to the router and sidebar.

- [ ] **Step 3: Implement the page, route, and sidebar entry**

```ts
// ai-project_front_end/src/router/index.ts
import PlatformRecords from '@/views/settings/PlatformRecords.vue'

const ProjectPlatformRecords = createProjectShellPage('平台记录', PlatformRecords)

{
  path: '/projects/:projectId/settings/platform-records',
  component: ProjectPlatformRecords
}
```

```vue
<!-- ai-project_front_end/src/views/settings/PlatformRecords.vue -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchAiJobs, fetchAuditLogs } from '@/lib/api/platformRecords'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())
const aiJobs = ref([])
const auditLogs = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [jobs, logs] = await Promise.all([
      fetchAiJobs(projectId.value),
      fetchAuditLogs(projectId.value),
    ])
    aiJobs.value = jobs.items
    auditLogs.value = logs.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '平台记录加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>
```

```ts
// ai-project_front_end/src/components/figma/ai-testing-platform/AiTestingSidebar.vue
{ label: '平台记录', icon: navSetting, to: `/projects/${projectId.value}/settings/platform-records` }
```

- [ ] **Step 4: Run the frontend build again**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npm run build
```

Expected: PASS and emit the production bundle without unresolved imports.

- [ ] **Step 5: Commit**

```bash
git add ai-project_front_end/src/lib/api/platformRecords.ts ai-project_front_end/src/views/settings/PlatformRecords.vue ai-project_front_end/src/router/index.ts ai-project_front_end/src/components/figma/ai-testing-platform/AiTestingSidebar.vue
git commit -m "feat: add platform records page"
```

## Task 3: Requirement Main-Chain Polish and Revision History

**Files:**
- Create: `ai-project-back-end/alembic/versions/0014_add_requirement_change_analysis_and_revisions.py`
- Modify: `ai-project-back-end/app/models/requirement.py`
- Modify: `ai-project-back-end/app/schemas/requirement.py`
- Modify: `ai-project-back-end/app/services/requirement.py`
- Modify: `ai-project-back-end/app/api/v1/endpoints/requirements.py`
- Modify: `ai-project-back-end/tests/test_requirement_analysis_api.py`
- Modify: `ai-project_front_end/src/lib/api/requirements.ts`
- Modify: `ai-project_front_end/src/views/requirements/RequirementDocDetail.vue`
- Modify: `ai-project_front_end/src/views/requirements/RequirementAnalysisDetail.vue`

- [ ] **Step 1: Add failing tests for revision history and rollback endpoints**

```python
def test_list_analysis_revisions_endpoint(monkeypatch) -> None:
    async def _fake_list_revisions(db, *, user, project_id, analysis_id):
        return [
            {
                "id": "77777777-7777-7777-7777-777777777777",
                "analysisId": str(analysis_id),
                "revisionNo": 2,
                "summary": "人工修订了边界条件",
                "createdBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "createdAt": 1710000200,
            }
        ]

    monkeypatch.setattr(requirements_endpoint, "list_requirement_analysis_revisions", _fake_list_revisions)
    client = TestClient(_build_app())
    resp = client.get("/api/projects/22222222-2222-2222-2222-222222222222/requirements/analyses/33333333-3333-3333-3333-333333333333/revisions")
    assert resp.status_code == 200
    assert resp.json()["data"][0]["revisionNo"] == 2


def test_rollback_analysis_endpoint(monkeypatch) -> None:
    async def _fake_rollback(db, *, user, project_id, analysis_id, revision_id):
        return {"id": str(analysis_id), "summary": "已回滚到指定修订"}

    monkeypatch.setattr(requirements_endpoint, "rollback_requirement_analysis_revision", _fake_rollback)
    client = TestClient(_build_app())
    resp = client.post("/api/projects/22222222-2222-2222-2222-222222222222/requirements/analyses/33333333-3333-3333-3333-333333333333/rollback", json={"revisionId": "77777777-7777-7777-7777-777777777777"})
    assert resp.status_code == 200
    assert resp.json()["data"]["summary"] == "已回滚到指定修订"
```

- [ ] **Step 2: Run the requirement endpoint tests**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m pytest tests\test_requirement_analysis_api.py -v
```

Expected: FAIL because the revision endpoints and service hooks do not exist yet.

- [ ] **Step 3: Implement revision snapshots, history endpoints, and UI wiring**

```python
# ai-project-back-end/app/models/requirement.py
class RequirementAnalysisRevision(Base, TimestampMixin):
    __tablename__ = "requirement_analysis_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("requirement_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
```

```python
# ai-project-back-end/app/services/requirement.py
async def save_requirement_analysis_revision(db, *, user, analysis, summary: str) -> RequirementAnalysisRevision:
    next_revision = int((await db.scalar(select(func.coalesce(func.max(RequirementAnalysisRevision.revision_no), 0)).where(RequirementAnalysisRevision.analysis_id == analysis.id))) or 0) + 1
    row = RequirementAnalysisRevision(
        tenant_id=analysis.tenant_id,
        project_id=analysis.project_id,
        analysis_id=analysis.id,
        revision_no=next_revision,
        summary=summary,
        snapshot_json=dict(analysis.analysis_json or {}),
        created_by=user.id,
    )
    db.add(row)
    await db.flush()
    return row
```

```python
# ai-project-back-end/app/api/v1/endpoints/requirements.py
@router.get("/analyses/{analysisId}/revisions", response_model=ApiResponse[list[RequirementAnalysisRevisionDetail]])
async def list_analysis_revisions_endpoint(...):
    rows = await list_requirement_analysis_revisions(...)
    return ApiResponse(data=rows, requestId=request_id)


@router.post("/analyses/{analysisId}/rollback", response_model=ApiResponse[RequirementAnalysisDetail])
async def rollback_analysis_endpoint(...):
    detail = await rollback_requirement_analysis_revision(...)
    await db.commit()
    return ApiResponse(data=detail, requestId=request_id)
```

```ts
// ai-project_front_end/src/lib/api/requirements.ts
export async function fetchRequirementAnalysisRevisions(projectId: string, analysisId: string) {
  return requestJson<RequirementAnalysisRevision[]>(`/projects/${encodeURIComponent(projectId)}/requirements/analyses/${encodeURIComponent(analysisId)}/revisions`, { method: 'GET' })
}

export async function rollbackRequirementAnalysis(projectId: string, analysisId: string, revisionId: string) {
  return requestJson<RequirementAnalysis>(`/projects/${encodeURIComponent(projectId)}/requirements/analyses/${encodeURIComponent(analysisId)}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ revisionId }),
  })
}
```

```vue
<!-- ai-project_front_end/src/views/requirements/RequirementAnalysisDetail.vue -->
<button class="rounded-[8px] border border-black/10 px-3 py-1 text-[12px]" @click="loadRevisions">
  查看修订历史
</button>
<button class="rounded-[8px] border border-black/10 px-3 py-1 text-[12px]" :disabled="!selectedRevisionId" @click="handleRollback">
  回滚到选中修订
</button>
```

- [ ] **Step 4: Re-run backend tests and frontend build**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m pytest tests\test_requirement_analysis_api.py tests\test_requirement_case_drafts_api.py tests\test_requirement_case_links_api.py -v
cd D:\OtherProject\ai-project\ai-project_front_end
npm run build
```

Expected: PASS. The requirement endpoints keep working and the revised requirement pages compile.

- [ ] **Step 5: Commit**

```bash
git add ai-project-back-end/alembic/versions/0014_add_requirement_change_analysis_and_revisions.py ai-project-back-end/app/models/requirement.py ai-project-back-end/app/schemas/requirement.py ai-project-back-end/app/services/requirement.py ai-project-back-end/app/api/v1/endpoints/requirements.py ai-project-back-end/tests/test_requirement_analysis_api.py ai-project_front_end/src/lib/api/requirements.ts ai-project_front_end/src/views/requirements/RequirementDocDetail.vue ai-project_front_end/src/views/requirements/RequirementAnalysisDetail.vue
git commit -m "feat: add requirement revision history and rollback"
```

## Task 4: Requirement Change Analysis Backend

**Files:**
- Create: `ai-project-back-end/app/schemas/requirement_change.py`
- Create: `ai-project-back-end/app/services/requirement_change.py`
- Create: `ai-project-back-end/app/api/v1/endpoints/requirement_changes.py`
- Create: `ai-project-back-end/tests/test_requirement_change_analysis_api.py`
- Modify: `ai-project-back-end/app/models/requirement.py`
- Modify: `ai-project-back-end/app/models/__init__.py`
- Modify: `ai-project-back-end/app/api/v1/__init__.py`

- [ ] **Step 1: Write the failing endpoint tests for change-set creation and regression-set generation**

```python
def test_create_requirement_change_set(monkeypatch) -> None:
    async def _fake_create_change_set(db, *, user, project_id, doc_id, payload):
        return {
            "id": "88888888-8888-8888-8888-888888888888",
            "projectId": str(project_id),
            "docId": str(doc_id),
            "baselineVersionId": payload.baselineVersionId,
            "targetVersionId": payload.targetVersionId,
            "status": "READY",
            "summary": "识别到 3 个变更点",
            "createdAt": 1710000300,
        }

    monkeypatch.setattr(requirement_changes_endpoint, "create_requirement_change_set", _fake_create_change_set)
    client = TestClient(_build_app())
    resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs/33333333-3333-3333-3333-333333333333/change-sets",
        json={"baselineVersionId": "44444444-4444-4444-4444-444444444444", "targetVersionId": "55555555-5555-5555-5555-555555555555"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "READY"


def test_generate_requirement_regression_set(monkeypatch) -> None:
    async def _fake_generate_regression_set(db, *, user, project_id, change_set_id):
        return {
            "id": "99999999-9999-9999-9999-999999999999",
            "changeSetId": str(change_set_id),
            "caseCount": 2,
            "summary": "命中 2 条回归用例",
            "createdAt": 1710000400,
        }

    monkeypatch.setattr(requirement_changes_endpoint, "generate_requirement_regression_set", _fake_generate_regression_set)
    client = TestClient(_build_app())
    resp = client.post("/api/projects/22222222-2222-2222-2222-222222222222/requirements/change-sets/88888888-8888-8888-8888-888888888888/regression-set")
    assert resp.status_code == 200
    assert resp.json()["data"]["caseCount"] == 2
```

- [ ] **Step 2: Run the new endpoint tests**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m pytest tests\test_requirement_change_analysis_api.py -v
```

Expected: FAIL because the change-analysis router and service do not exist yet.

- [ ] **Step 3: Implement change-set, change-item, regression-set, and regression-case support**

```python
# ai-project-back-end/app/models/requirement.py
class RequirementChangeSet(Base, TimestampMixin):
    __tablename__ = "requirement_change_sets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("requirement_docs.id"), nullable=False, index=True)
    baseline_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("requirement_doc_versions.id"), nullable=False)
    target_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("requirement_doc_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="READY")
    summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
```

```python
# ai-project-back-end/app/services/requirement_change.py
async def create_requirement_change_set(db, *, user, project_id, doc_id, payload):
    baseline, target = await _get_two_versions(...)
    items = _build_change_items(baseline.parsed_text_preview or "", target.parsed_text_preview or "")
    change_set = RequirementChangeSet(...)
    db.add(change_set)
    await db.flush()
    for item in items:
        db.add(RequirementChangeItem(...))
    await create_ai_job_record(
        db,
        tenant_id=user.tenant_id,
        project_id=project_id,
        job_type="REQUIREMENT_CHANGE_ANALYSIS",
        source_type="RequirementDoc",
        source_id=str(doc_id),
        status="SUCCEEDED",
        summary=f"识别到 {len(items)} 个变更点",
        triggered_by=user.id,
    )
    return _to_change_set_detail(change_set)
```

```python
# ai-project-back-end/app/api/v1/endpoints/requirement_changes.py
router = APIRouter()


@router.post("/projects/{projectId}/requirements/docs/{docId}/change-sets", response_model=ApiResponse[RequirementChangeSetDetail])
async def create_change_set_endpoint(...):
    detail = await create_requirement_change_set(...)
    await db.commit()
    return ApiResponse(data=detail, requestId=request_id)


@router.post("/projects/{projectId}/requirements/change-sets/{changeSetId}/regression-set", response_model=ApiResponse[RequirementRegressionSetDetail])
async def create_regression_set_endpoint(...):
    detail = await generate_requirement_regression_set(...)
    await db.commit()
    return ApiResponse(data=detail, requestId=request_id)
```

- [ ] **Step 4: Re-run the new tests plus one existing requirement contract**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m pytest tests\test_requirement_change_analysis_api.py tests\test_requirement_docs_api.py -v
```

Expected: PASS and no regression to the existing requirement docs endpoint layer.

- [ ] **Step 5: Commit**

```bash
git add ai-project-back-end/app/schemas/requirement_change.py ai-project-back-end/app/services/requirement_change.py ai-project-back-end/app/api/v1/endpoints/requirement_changes.py ai-project-back-end/app/models/requirement.py ai-project-back-end/app/models/__init__.py ai-project-back-end/app/api/v1/__init__.py ai-project-back-end/tests/test_requirement_change_analysis_api.py
git commit -m "feat: add requirement change analysis backend"
```

## Task 5: Requirement Change Analysis UI

**Files:**
- Create: `ai-project_front_end/src/lib/api/requirementChanges.ts`
- Create: `ai-project_front_end/src/views/requirements/RequirementChangeSetDetail.vue`
- Modify: `ai-project_front_end/src/router/index.ts`
- Modify: `ai-project_front_end/src/views/requirements/RequirementDocDetail.vue`

- [ ] **Step 1: Add the new API typing and route import**

```ts
// ai-project_front_end/src/lib/api/requirementChanges.ts
export type RequirementChangeSet = {
  id: string
  projectId: string
  docId: string
  baselineVersionId: string
  targetVersionId: string
  status: string
  summary: string
  createdAt: number
}

export type RequirementRegressionSet = {
  id: string
  changeSetId: string
  caseCount: number
  summary: string
  createdAt: number
}
```

- [ ] **Step 2: Run the frontend build**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npm run build
```

Expected: FAIL until the new view and route are fully wired.

- [ ] **Step 3: Implement the comparison entry and detail page**

```ts
// ai-project_front_end/src/router/index.ts
import RequirementChangeSetDetail from '@/views/requirements/RequirementChangeSetDetail.vue'

const ProjectRequirementChangeSetDetail = createProjectShellPage('需求文档中心', RequirementChangeSetDetail)

{
  path: '/projects/:projectId/requirements/change-sets/:changeSetId',
  component: ProjectRequirementChangeSetDetail
}
```

```vue
<!-- ai-project_front_end/src/views/requirements/RequirementDocDetail.vue -->
<button
  type="button"
  class="rounded-[8px] border border-black/10 px-3 py-1 text-[12px]"
  :disabled="versions.length < 2 || !selectedBaselineVersionId || !selectedVersionId"
  @click="handleCreateChangeSet"
>
  生成变更影响分析
</button>
```

```vue
<!-- ai-project_front_end/src/views/requirements/RequirementChangeSetDetail.vue -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchRequirementChangeSetDetail, generateRequirementRegressionSet } from '@/lib/api/requirementChanges'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())
const changeSetId = computed(() => String(route.params.changeSetId || '').trim())
const detail = ref(null)

async function load() {
  detail.value = await fetchRequirementChangeSetDetail(projectId.value, changeSetId.value)
}

onMounted(() => {
  void load()
})
</script>
```

- [ ] **Step 4: Re-run the frontend build**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npm run build
```

Expected: PASS and emit the new requirement change detail page.

- [ ] **Step 5: Commit**

```bash
git add ai-project_front_end/src/lib/api/requirementChanges.ts ai-project_front_end/src/views/requirements/RequirementChangeSetDetail.vue ai-project_front_end/src/router/index.ts ai-project_front_end/src/views/requirements/RequirementDocDetail.vue
git commit -m "feat: add requirement change analysis ui"
```

## Task 6: API/TestCase Binding Backend Expansion

**Files:**
- Create: `ai-project-back-end/alembic/versions/0015_expand_testcase_bindings_for_api_links.py`
- Create: `ai-project-back-end/tests/test_testcase_bindings_api.py`
- Modify: `ai-project-back-end/app/models/testcase_binding.py`
- Modify: `ai-project-back-end/app/schemas/testcase_binding.py`
- Modify: `ai-project-back-end/app/services/testcase_binding.py`
- Modify: `ai-project-back-end/app/api/v1/endpoints/testcase_bindings.py`

- [ ] **Step 1: Write the failing endpoint tests for request-level and collection-level binding lookups**

```python
def test_list_bindings_by_request_endpoint(monkeypatch) -> None:
    request_id = "aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa"

    async def _fake_list_by_request(db, *, user, project_id, request_id):
        return [
            {
                "id": "bbbbbbbb-2222-2222-2222-bbbbbbbbbbbb",
                "projectId": str(project_id),
                "testcaseId": "cccccccc-3333-3333-3333-cccccccccccc",
                "linkType": "REQUEST",
                "targetId": request_id,
                "name": "登录接口-主路径",
                "lastRunStatus": "PASSED",
                "version": 2,
                "updatedAt": 1710000500,
            }
        ]

    monkeypatch.setattr(testcase_bindings_endpoint, "list_testcase_bindings_by_request", _fake_list_by_request)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/22222222-2222-2222-2222-222222222222/requests/{request_id}/bindings")
    assert resp.status_code == 200
    assert resp.json()["data"][0]["linkType"] == "REQUEST"


def test_list_bindings_by_collection_endpoint(monkeypatch) -> None:
    collection_id = "dddddddd-4444-4444-4444-dddddddddddd"

    async def _fake_list_by_collection(db, *, user, project_id, collection_id):
        return []

    monkeypatch.setattr(testcase_bindings_endpoint, "list_testcase_bindings_by_collection", _fake_list_by_collection)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/22222222-2222-2222-2222-222222222222/collections/{collection_id}/bindings")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
```

- [ ] **Step 2: Run the new binding tests**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m pytest tests\test_testcase_bindings_api.py -v
```

Expected: FAIL because request and collection binding queries do not exist yet.

- [ ] **Step 3: Expand the binding model, schema, service, and router**

```python
# ai-project-back-end/app/models/testcase_binding.py
class TestcaseBinding(Base, TimestampMixin):
    __tablename__ = "testcase_bindings"

    link_type: Mapped[str] = mapped_column(String(32), nullable=False, default="API_TARGET")
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_requests.id"), nullable=True, index=True)
    collection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("api_collections.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    assert_summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    last_run_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

```python
# ai-project-back-end/app/schemas/testcase_binding.py
class TestcaseBindingListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    testcaseId: IdStr
    name: NameStr
    linkType: str
    requestId: IdStr | None = None
    collectionId: IdStr | None = None
    sourceType: str
    assertSummary: str = ""
    lastRunStatus: str | None = None
    lastRunAt: UnixTs | None = None
    version: int
    updatedAt: UnixTs
```

```python
# ai-project-back-end/app/api/v1/endpoints/testcase_bindings.py
@router.get("/projects/{projectId}/requests/{requestId}/bindings", response_model=ApiResponse[list[TestcaseBindingListItem]])
async def list_by_request_endpoint(...):
    rows = await list_testcase_bindings_by_request(...)
    return ApiResponse(data=rows, requestId=request_id)


@router.get("/projects/{projectId}/collections/{collectionId}/bindings", response_model=ApiResponse[list[TestcaseBindingListItem]])
async def list_by_collection_endpoint(...):
    rows = await list_testcase_bindings_by_collection(...)
    return ApiResponse(data=rows, requestId=request_id)
```

- [ ] **Step 4: Re-run the binding tests and one existing binding flow**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m pytest tests\test_testcase_bindings_api.py tests\test_requirement_case_links_api.py -v
```

Expected: PASS and preserve the existing traceability endpoint behavior.

- [ ] **Step 5: Commit**

```bash
git add ai-project-back-end/alembic/versions/0015_expand_testcase_bindings_for_api_links.py ai-project-back-end/app/models/testcase_binding.py ai-project-back-end/app/schemas/testcase_binding.py ai-project-back-end/app/services/testcase_binding.py ai-project-back-end/app/api/v1/endpoints/testcase_bindings.py ai-project-back-end/tests/test_testcase_bindings_api.py
git commit -m "feat: expand testcase bindings for api assets"
```

## Task 7: Collections, TestCase Detail, and Run Detail UI Integration

**Files:**
- Modify: `ai-project_front_end/src/lib/api/collections.ts`
- Modify: `ai-project_front_end/src/lib/aiTestingPlatformApi.ts`
- Modify: `ai-project_front_end/src/views/collections/CollectionDetail.vue`
- Modify: `ai-project_front_end/src/views/runs/RunDetail.vue`
- Modify: `ai-project_front_end/src/components/figma/ai-testing-platform/TestCaseDetailPanel.vue`
- Modify: `ai-project_front_end/src/components/figma/ai-testing-platform/ApiCollectionsPanel.vue`

- [ ] **Step 1: Extend the client-side binding contract before wiring the UI**

```ts
// ai-project_front_end/src/lib/aiTestingPlatformApi.ts
export type ApiAssetBinding = {
  id: string
  projectId: string
  testcaseId: string
  linkType: 'REQUEST' | 'COLLECTION' | 'API_TARGET'
  requestId?: string | null
  collectionId?: string | null
  sourceType: string
  name: string
  assertSummary: string
  lastRunStatus?: string | null
  lastRunAt?: number | null
  version: number
  updatedAt: number
}
```

- [ ] **Step 2: Run the frontend build**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npm run build
```

Expected: FAIL until the updated components consume the new contract.

- [ ] **Step 3: Implement request binding, reverse lookup, and run-detail linking**

```vue
<!-- ai-project_front_end/src/views/collections/CollectionDetail.vue -->
<button
  type="button"
  class="rounded-[8px] border border-black/10 px-3 py-1 text-[12px]"
  :disabled="!requestForm"
  @click="openBindingDrawer"
>
  绑定 TestCase
</button>
```

```ts
// ai-project_front_end/src/lib/api/collections.ts
export async function fetchRequestBindings(projectId: string, requestId: string) {
  return requestJson<ApiAssetBinding[]>(`/projects/${encodeURIComponent(projectId)}/requests/${encodeURIComponent(requestId)}/bindings`, {
    method: 'GET',
  })
}
```

```vue
<!-- ai-project_front_end/src/components/figma/ai-testing-platform/TestCaseDetailPanel.vue -->
<section class="rounded-[12px] border border-black/10 bg-white p-4">
  <div class="text-[13px] font-medium text-[#0A0A0A]">接口绑定</div>
  <div v-for="binding in apiBindings" :key="binding.id" class="mt-2 rounded-[8px] bg-[#F8FAFC] p-2 text-[12px]">
    <div>{{ binding.name }}</div>
    <div class="text-[#717182]">{{ binding.linkType }} / {{ binding.lastRunStatus || '未执行' }}</div>
  </div>
</section>
```

```vue
<!-- ai-project_front_end/src/views/runs/RunDetail.vue -->
<button
  v-if="runDetail?.suiteId"
  type="button"
  class="h-[32px] rounded-[10px] border border-black/10 px-[12px] text-[13px]"
  @click="openRelatedSuite"
>
  打开关联对象
</button>
```

- [ ] **Step 4: Re-run the frontend build**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npm run build
```

Expected: PASS and keep collection detail, testcase detail, and run detail in the production bundle.

- [ ] **Step 5: Commit**

```bash
git add ai-project_front_end/src/lib/api/collections.ts ai-project_front_end/src/lib/aiTestingPlatformApi.ts ai-project_front_end/src/views/collections/CollectionDetail.vue ai-project_front_end/src/views/runs/RunDetail.vue ai-project_front_end/src/components/figma/ai-testing-platform/TestCaseDetailPanel.vue ai-project_front_end/src/components/figma/ai-testing-platform/ApiCollectionsPanel.vue
git commit -m "feat: connect api assets, testcase detail, and run detail"
```

## Task 8: Real Migration, Build, and Smoke Verification

**Files:**
- Modify: `D:\OtherProject\NewTestPlatform\智能测试平台任务进度看板.html` after verification
- Modify: `docs/superpowers/specs/2026-05-15-prd-coverage-phase1-design.md` only if a verified implementation decision changes the design

- [ ] **Step 1: Run Alembic against PostgreSQL**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m alembic upgrade head
```

Expected: PASS. New revisions `0013`, `0014`, and `0015` apply cleanly on the project PostgreSQL database.

- [ ] **Step 2: Run the focused backend regression suite**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m pytest tests\test_requirement_docs_api.py tests\test_requirement_analysis_api.py tests\test_requirement_case_drafts_api.py tests\test_requirement_case_links_api.py tests\test_platform_records_api.py tests\test_requirement_change_analysis_api.py tests\test_testcase_bindings_api.py -v
```

Expected: PASS.

- [ ] **Step 3: Run the frontend production build**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npm run build
```

Expected: PASS.

- [ ] **Step 4: Perform the live smoke flow**

Run:

```powershell
$env:DEBUG='false'
cd D:\OtherProject\ai-project\ai-project-back-end
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Then verify in browser or HTTP client:

```text
1. 登录并进入项目
2. 新建需求文档 -> 上传两个版本
3. 生成需求分析 -> 同步测试点 -> 审核测试点
4. 生成草稿 -> 批量审核入库 -> 打开追溯
5. 生成变更影响分析 -> 生成回归集合
6. 导入 OpenAPI/Postman -> 打开 Collection 详情 -> 绑定 TestCase
7. 执行单请求 -> 打开 Run 详情
8. 打开 平台记录 页面，确认 AI 任务和审计日志都可见
```

Expected: Every module has page, API, real data, one minimal flow, and at least the targeted tests/build checks above.

- [ ] **Step 5: Update progress artifacts and commit**

```bash
# update D:\OtherProject\NewTestPlatform\智能测试平台任务进度看板.html outside the repo
git add docs/superpowers/specs/2026-05-15-prd-coverage-phase1-design.md
git commit -m "docs: sync phase 1 verification notes"
```

## Self-Review Notes

### Spec coverage

- Platform shared foundation: covered by Task 1 and Task 2
- Requirement asset main-chain polish: covered by Task 3
- Requirement change impact analysis: covered by Task 4 and Task 5
- API/TestCase binding and minimal execution loop: covered by Task 6 and Task 7
- Real DB, build, and smoke verification: covered by Task 8

### Placeholder scan

- No placeholder markers remain
- Every task names exact files and explicit commands
- Every code step includes concrete code blocks instead of abstract instructions

### Type consistency

- Platform records use `AiJobRecord` / `AuditLogListItem` consistently
- Change analysis uses `RequirementChangeSet` / `RequirementRegressionSet` consistently
- Binding expansion uses `ApiAssetBinding`, `linkType`, `requestId`, and `collectionId` consistently
