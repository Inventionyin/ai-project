---
name: ui-figma-playwright-validator
description: Generates and runs Playwright UI checks from Figma page metadata. Invoke when user asks to validate a page by pageId or generate-and-run UI specs.
alwaysApply: false
---

# Figma 页面 UI 自动化验证器

## 功能概述
该技能用于基于 `pageId` 一键完成以下动作：
1. 读取 `docs/figma/manifest.json` 与页面描述文档。
2. 生成或更新 Playwright Spec 到 `ai-project_front_end/tests/ui/generated/`。
3. 执行用例并输出报告到 `ai-project_front_end/tests/ui/reports/html`。
4. 回填执行结果到 `manifest.json` 的 `uiAutomation` 字段。

## 触发条件
- 用户说“按 pageId 生成并执行 UI 自动化”
- 用户说“一键跑某个 Figma 页面验证”
- 用户说“创建/更新某页面的 Playwright spec 并执行”

## 输入约定
- 必填：`pageId`
- 可选：`assertLevel`（P0/P1/P2，默认 P0）
- 可选：`headed`（是否有头执行，默认 false）

## 依赖前提
- 前端目录：`ai-project_front_end/`
- Playwright 已接入（`package.json` 含 `test:e2e` 脚本）
- `manifest.json` 存在目标页面记录，且至少包含：
  - `id`
  - `routePath`
  - `envUrl` 或可由 `playwright.config.ts` 中 `baseURL` 访问
  - `pageDoc`

## 执行流程
1. **读取清单**
   - 打开 `docs/figma/manifest.json`，按 `pageId` 定位页面项。
   - 若不存在，立即返回错误并给出可选 `pageId` 列表。
2. **读取页面文档**
   - 打开 `pageDoc` 指向的 Markdown。
   - 在 `页面固定字段（P0）` 中提取标题、副标题、主按钮、导航文本。
3. **生成 Spec**
   - 目标文件：`ai-project_front_end/tests/ui/generated/<pageId>.spec.ts`
   - P0：生成文本可见性断言与 URL 断言。
   - P1：若文档包含关键区域与 baseline 信息，补充区域截图断言。
   - P2：若文档开启全页视觉，补充整页截图断言。
4. **执行测试**
   - 默认命令：`npm run test:e2e -- tests/ui/generated/<pageId>.spec.ts`
   - `headed=true` 时使用：`npm run test:e2e:headed -- tests/ui/generated/<pageId>.spec.ts`
5. **回填结果**
   - 更新 `manifest.json` 对应页面：
     - `updatedAt`
     - `uiAutomation.status`（verified/failed）
     - `uiAutomation.specPath`
     - `uiAutomation.reportDir`
     - `uiAutomation.lastRunAt`
     - `uiAutomation.lastResult`
6. **输出摘要**
   - 返回：执行命令、通过/失败数、报告路径、失败截图路径（如有）。

## 生成规则
- 断言优先级：语义选择器 > 可见文本 > CSS 选择器。
- 同类按钮可能重名时使用精确文案，避免 strict mode 冲突。
- 用例命名：`<pageId> <assertLevel> 验证`。
- 不修改业务组件代码，仅新增/更新测试文件与文档字段。

## 失败处理
- `manifest` 缺字段：提示缺失字段并终止。
- 页面元素不稳定：标记为 `failed`，记录失败断言与截图路径。
- 视觉基线缺失：自动降级仅执行 P0 文本断言，并在结果中说明。

## 使用示例
- “用 `sample-login-page` 一键生成并执行 UI 验证（P0）”
- “用 `sample-login-page` 跑 P1，更新 spec 并输出报告”
- “对 `sample-login-page` 以 headed 模式执行自动化”
