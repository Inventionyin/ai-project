# Meeting UX Open Source Reuse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first low-risk meeting-driven UX improvements using the open-source research as guidance without importing heavy product code.

**Architecture:** Keep the first slice frontend-only and compatible with the existing Vue + Tailwind + Playwright stack. Use product patterns inspired by ECharts/GridStack, Bruno/Hoppscotch, and TCMS tools, but do not add new runtime dependencies until the existing pages prove the interaction model.

**Tech Stack:** Vue 3, Vue Router, Tailwind CSS, Playwright.

---

### Task 1: Dashboard Filter Controls

**Files:**
- Modify: `ai-project_front_end/tests/ui/generated/product-information-architecture.spec.ts`
- Modify: `ai-project_front_end/src/views/dashboard/Overview.vue`

- [ ] **Step 1: Write the failing E2E assertion**

Add assertions to the dashboard customization test:

```ts
await expect(page.getByLabel('时间范围')).toBeVisible()
await expect(page.getByLabel('统计维度')).toBeVisible()
await page.getByLabel('时间范围').selectOption('14')
await page.getByLabel('统计维度').selectOption('module')
await expect(page.getByText('当前筛选：近 14 天 · 按模块')).toBeVisible()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npx playwright test tests/ui/generated/product-information-architecture.spec.ts --project=chromium -g "仪表盘支持自定义模块显示并持久保存"
```

Expected: FAIL because the filter labels do not exist yet.

- [ ] **Step 3: Implement minimal UI state**

In `Overview.vue`, add `dashboardFilters` with `days` and `dimension`, add computed display text, and render two select controls near the dashboard header.

- [ ] **Step 4: Run the targeted test**

Expected: PASS.

### Task 2: Asset Center Unified Operations

**Files:**
- Modify: `ai-project_front_end/tests/ui/generated/product-information-architecture.spec.ts`
- Modify: `ai-project_front_end/src/views/workspace/WorkspaceSectionHome.vue`

- [ ] **Step 1: Write the failing E2E assertion**

Add assertions to the workspace home test under the `/projects/1/assets` section:

```ts
await expect(page.getByLabel('选择资产操作')).toBeVisible()
await expect(page.getByText('统一资产操作')).toBeVisible()
await page.getByLabel('选择资产操作').selectOption('批量编辑')
await expect(page.getByText('批量编辑字段、标签、模块和关联关系')).toBeVisible()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npx playwright test tests/ui/generated/product-information-architecture.spec.ts --project=chromium -g "四个一级工作台首页显示聚合指标和操作入口"
```

Expected: FAIL because the operation selector does not exist yet.

- [ ] **Step 3: Implement minimal operation selector**

In `WorkspaceSectionHome.vue`, add an assets-only operation selector with options: 导入, 导出, 上传, 编辑, 删除, 批量编辑. Render it in the asset workflow section as a compact select + detail area.

- [ ] **Step 4: Run the targeted test**

Expected: PASS.

### Task 3: AI Candidate Review Gate

**Files:**
- Modify: `ai-project_front_end/tests/ui/generated/product-information-architecture.spec.ts`
- Modify: `ai-project_front_end/src/components/figma/ai-testing-platform/AiAssistantPanel.vue`

- [ ] **Step 1: Write the failing E2E assertion**

Add assertions to the AI generation test:

```ts
await expect(page.getByText('文档检查')).toBeVisible()
await expect(page.getByText('候选用例')).toBeVisible()
await expect(page.getByText('人工确认')).toBeVisible()
await expect(page.getByText('正式入库')).toBeVisible()
await expect(page.getByText('生成并导入到用例列表')).not.toBeVisible()
await expect(page.getByText('生成候选用例，确认后入库')).toBeVisible()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npx playwright test tests/ui/generated/product-information-architecture.spec.ts --project=chromium -g "AI生成页用下拉选择智能体类型"
```

Expected: FAIL because staged workflow labels and safer copy are not present yet.

- [ ] **Step 3: Implement minimal staged workflow copy**

In `AiAssistantPanel.vue`, add a compact staged workflow strip above the agent selector. Rename the direct import button to safer review-gated copy and make it clearly generate candidates first instead of implying blind import.

- [ ] **Step 4: Run the targeted test**

Expected: PASS.

### Task 4: Verification

**Files:**
- Verify only, no new source files.

- [ ] **Step 1: Run product information architecture E2E**

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npx playwright test tests/ui/generated/product-information-architecture.spec.ts --project=chromium
```

- [ ] **Step 2: Run frontend build**

```powershell
cd D:\OtherProject\ai-project\ai-project_front_end
npm run build
```

- [ ] **Step 3: Record outcome**

Update the final response with changed files and verification results.
