# Delivery Operations Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the current acceptance version with delivery documentation, a demo route, one-click operations commands, and a small in-platform guidance polish.

**Architecture:** Keep the project stable by adding documentation and a thin script wrapper around existing verification scripts. Frontend changes are limited to the existing production acceptance center and generated Playwright coverage.

**Tech Stack:** Markdown docs, PowerShell 7-compatible scripts, Vue 3, Playwright, Vite build.

---

### Task 1: Delivery Documentation

**Files:**
- Create: `docs/final-delivery-package-20260526.md`
- Create: `docs/demo-script-20260526.md`

- [ ] Add an acceptance delivery package that summarizes scope, evidence, CI links, external-system rerun evidence, data state, and known operating boundaries.
- [ ] Add a 5-10 minute demo route from login through dashboard, asset import/governance, API debugging, suite run, run detail, acceptance report, and operations evidence.

### Task 2: Operations Entry Point

**Files:**
- Create: `scripts/operate.ps1`
- Modify: `scripts/README.md`
- Modify: `README.md`

- [ ] Add a PowerShell entry script with actions for `help`, `start`, `stop`, `local-gate`, `backend-e2e`, `frontend-build`, `performance`, `production`, `external`, `delivery-check`, and `all-dry-run`.
- [ ] Update script documentation so maintainers know which command to run for daily checks, acceptance checks, and production checks.
- [ ] Link the delivery package and demo route from the root README.

### Task 3: Acceptance Center Guidance Polish

**Files:**
- Modify: `ai-project_front_end/src/views/settings/AcceptanceCenter.vue`
- Modify: `ai-project_front_end/tests/ui/generated/product-information-architecture.spec.ts`

- [ ] Add a compact "验收演示路线" block to the acceptance center so the platform itself shows the acceptance walkthrough.
- [ ] Keep the block static and frontend-only; no backend API or database change.
- [ ] Extend generated Playwright coverage to assert the new guidance is visible.

### Task 4: Verification

**Commands:**
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\operate.ps1 -Action help`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\operate.ps1 -Action all-dry-run`
- `cd ai-project_front_end && npm run build`
- `cd ai-project_front_end && npx playwright test tests/ui/generated/product-information-architecture.spec.ts --project=chromium --reporter=line`

- [ ] Run script smoke checks.
- [ ] Run frontend build.
- [ ] Run focused Playwright coverage.
- [ ] Report any residual risks without claiming more than the evidence proves.
