# Acceptance Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a product-visible production acceptance center that aggregates project data readiness, external integration readiness, operations health, and exportable acceptance reporting.

**Architecture:** Add a backend acceptance service under project routes that reuses trial-operation dashboard, notification diagnostics, DevOps pipeline metadata, and ops health checks. Add a Vue settings page that presents the acceptance gate and copies Markdown evidence for stakeholder reporting.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic schemas, Vue 3, TypeScript, Playwright.

---

### Task 1: Backend Acceptance Center

**Files:**
- Create: `ai-project-back-end/app/schemas/acceptance.py`
- Create: `ai-project-back-end/app/services/acceptance.py`
- Create: `ai-project-back-end/app/api/v1/endpoints/acceptance.py`
- Modify: `ai-project-back-end/app/api/v1/__init__.py`
- Test: `ai-project-back-end/tests/test_acceptance_center_api.py`

- [ ] Write failing tests for summary and report endpoints.
- [ ] Implement schemas with explicit readiness/check/report types.
- [ ] Implement service aggregation with masked configuration fields.
- [ ] Register project routes under `/api/projects/{projectId}/acceptance`.
- [ ] Verify tests pass.

### Task 2: Frontend Acceptance Center

**Files:**
- Create: `ai-project_front_end/src/lib/api/acceptance.ts`
- Create: `ai-project_front_end/src/views/settings/AcceptanceCenter.vue`
- Modify: `ai-project_front_end/src/router/index.ts`
- Test: `ai-project_front_end/tests/ui/generated/acceptance-center.spec.ts`

- [ ] Write Playwright test for summary cards, external systems table, and report copy action.
- [ ] Implement API client.
- [ ] Implement operator-focused settings page.
- [ ] Register route `/projects/:projectId/settings/acceptance`.
- [ ] Verify Playwright and build pass.

### Task 3: Verification And PR

**Files:**
- Modify as needed: `scripts/README.md`

- [ ] Run backend focused tests.
- [ ] Run frontend Playwright test.
- [ ] Run frontend build.
- [ ] Commit, push branch, and create PR.
