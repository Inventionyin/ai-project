# 批量执行抽屉 & Allure 报告页改造方案

## 目标（对应需求 1~4）

1. 批量执行抽屉：点击“执行”后关闭抽屉。
2. 批量执行抽屉：移除“生成报告”按钮。
3. 测试用例执行完成后提示：页面消息提示“用例执行完成，可以查看报告”。
4. Allure 报告页面：左侧展示历史执行的报告文件列表；点击选中后加载对应 Allure 报告（展示方式与当前“批量执行-生成报告”打开的报告一致，即 iframe 加载 `/api/runs/{runId}/allure-report/`）。

## 现状定位（关键文件）

前端：
- 批量执行抽屉组件：[BatchRunDrawer.vue](file:///d:/ai-project/ai-project_front_end/src/components/figma/ai-testing-platform/BatchRunDrawer.vue)
- 用例管理页（抽屉挂载、执行逻辑、轮询、生成报告入口）：[CasesPanel.vue](file:///d:/ai-project/ai-project_front_end/src/components/figma/ai-testing-platform/CasesPanel.vue)
- Allure 报告页面（仅根据 query.runId iframe 加载）：[AllureReportPanel.vue](file:///d:/ai-project/ai-project_front_end/src/components/figma/ai-testing-platform/AllureReportPanel.vue)
- 左侧菜单包含 Allure 报告入口：[AiTestingSidebar.vue](file:///d:/ai-project/ai-project_front_end/src/components/figma/ai-testing-platform/AiTestingSidebar.vue)

后端：
- Allure 报告静态资源服务与生成接口：[runs.py](file:///d:/ai-project/ai-project-back-end/app/api/v1/endpoints/runs.py)
- Allure 报告 artifact 写入（kind=ALLURE_REPORT）：[runner_pytest_allure.py](file:///d:/ai-project/ai-project-back-end/app/services/runner_pytest_allure.py)

## 设计决策（关键行为）

### A. “执行”关闭抽屉，但执行状态仍可跟踪

问题点：
- 现有轮询逻辑 `scheduleBatchRunStatusPoll` 会在抽屉关闭时停止（以 `isBatchRunDrawerOpen` 为前置条件），且 `closeBatchRunDrawer` 会清空 runId 并停止轮询。
- 如果按需求点击“执行”立刻关闭抽屉，将导致无法触发“执行完成提示”。

方案：
- 将“抽屉是否打开”和“批量执行任务的生命周期状态”解耦。
- 点击“执行”后：
  - 保留 `batchRunRunId` 与执行状态（executing/completed），并启动/继续轮询。
  - 仅关闭 UI（`isBatchRunDrawerOpen=false`），不清空 runId、不清 timer。
- 轮询完成后统一触发 toast：“用例执行完成，可以查看报告”。

落地改动点（前端）：
- [CasesPanel.vue](file:///d:/ai-project/ai-project_front_end/src/components/figma/ai-testing-platform/CasesPanel.vue)
  - 调整 `closeBatchRunDrawer()`：只关闭抽屉，不停止执行中的轮询、不清空 runId（仅在“未开始/已结束且用户主动关闭”的场景清理）。
  - 调整 `scheduleBatchRunStatusPoll(runId)`：去掉对 `isBatchRunDrawerOpen` 的依赖；以 `batchRunRunId` 是否匹配作为唯一有效性判断，避免旧 runId 干扰。
  - 在检测到全部用例进入终态（PASSED/FAILED/SKIPPED/CANCELLED）时：
    - 更新状态为 completed
    - 触发 `showToast('用例执行完成，可以查看报告')`
    - 停止轮询
  - 为避免重复提示，加一个“已提示”标志（例如 `hasNotifiedBatchCompleted`），在开始新批量执行时重置。

### B. 批量执行抽屉移除“生成报告”按钮

落地改动点（前端）：
- [BatchRunDrawer.vue](file:///d:/ai-project/ai-project_front_end/src/components/figma/ai-testing-platform/BatchRunDrawer.vue)
  - 移除“生成报告”按钮 UI。
  - 同步移除相关 props / emits（`canGenerateReport`、`generate-report`）及父组件传参/监听。
- [CasesPanel.vue](file:///d:/ai-project/ai-project_front_end/src/components/figma/ai-testing-platform/CasesPanel.vue)
  - 删除/停用 `openBatchReport()` 以及抽屉上 `@generate-report` 绑定；如其他地方复用该函数，则保留并改为报告中心入口调用。

说明：
- 后端在 `PYTEST_ALLURE` runner 流程中会生成并落库 ALLURE_REPORT artifact，因此“查看报告”不再依赖抽屉内手动生成按钮。
- 若存在其他 runner 不生成报告，需要另行梳理（本次按当前抽屉 meta.runnerType=PYTEST_ALLURE 先落地）。

### C. “执行”按钮关闭抽屉的触发时机

规则：
- 先校验 projectId、勾选项、envId 等基础条件；校验失败不关闭抽屉，提示错误。
- 校验通过并成功创建 run（拿到 runId）后关闭抽屉。

落地改动点（前端）：
- [CasesPanel.vue](file:///d:/ai-project/ai-project_front_end/src/components/figma/ai-testing-platform/CasesPanel.vue)
  - 将抽屉 `@execute` 事件处理改为包装函数（如 `onDrawerExecute()`）：
    - 调用现有 `executeBatchRunFromDrawer()`
    - 在成功获取 runId 后 `isBatchRunDrawerOpen=false`

## D. Allure 报告页增加历史报告列表（左侧）

### 前端 UI/交互

目标体验：
- 进入 `/projects/:projectId/reports/allure` 时：
  - 左侧列表展示历史报告（按时间倒序）
  - 右侧展示选中报告的 iframe
- 支持 URL 直达：
  - `?runId=xxx`：默认选中该 runId 并加载
  - 无 `runId`：默认选中列表第一项

落地改动点（前端）：
- [AllureReportPanel.vue](file:///d:/ai-project/ai-project_front_end/src/components/figma/ai-testing-platform/AllureReportPanel.vue)
  - 页面布局改为左右两栏（左列表 / 右内容）。
  - 新增数据加载：
    - 从 route.params 取 `projectId`
    - 调用新接口拉取历史报告列表
  - 列表项展示建议：
    - 主标题：格式化时间（artifact createdAt 或 run startAt）
    - 副标题：runId（可展示短版，完整 runId 放 tooltip）
  - 选中项行为：
    - 更新路由 query.runId（便于刷新/分享）
    - 更新 iframeSrc 加载 `/api/runs/{runId}/allure-report/`（保持当前 token 拼接逻辑）
  - 空态：
    - 列表为空：提示“暂无历史报告”
    - 选中项加载失败（iframe 404）：提示“报告不存在或尚未生成”（可选：提供“重新生成”按钮，调用既有 generate 接口）

### 前端 API 封装

- [aiTestingPlatformApi.ts](file:///d:/ai-project/ai-project_front_end/src/lib/aiTestingPlatformApi.ts)
  - 增加 `fetchProjectAllureReports(projectId, page, pageSize)` 方法，返回历史报告列表。

### 后端接口（建议新增）

目的：
- 提供“只返回已存在的 Allure 报告 artifact”的列表，避免前端拉全量 runs 再逐个探测。

接口建议：
- `GET /api/runs/allure-reports?projectId=...&page=1&pageSize=50`

返回字段建议（每条）：
- `runId`
- `createdAt`（artifact.created_at 的 unix ts）
- `name`（meta_json.name，默认 `allure-report.zip`）
- `size`
- `reportUrl`（`/api/runs/{runId}/allure-report/`，前端通常只需要 runId）

实现要点（后端）：
- [runs.py](file:///d:/ai-project/ai-project-back-end/app/api/v1/endpoints/runs.py)
  - 新增路由 handler `list_allure_reports_`
  - SQL 逻辑：
    - Artifact.tenant_id == user.tenant_id
    - Artifact.type == LOG_BUNDLE
    - Artifact.meta_json.kind == 'ALLURE_REPORT'
    - join Run 按 project_id 过滤
    - order_by Artifact.created_at desc
    - 分页
- [schemas/run.py](file:///d:/ai-project/ai-project-back-end/app/schemas/run.py)
  - 新增 `RunAllureReportListItem` / `RunAllureReportListData(PageData[...])`

## 验收标准（可直接对照测试）

1. 打开批量执行抽屉后点击“执行”，抽屉关闭；执行被成功发起（仍能在网络/后端看到 run 已创建）。
2. 批量执行抽屉底部不再出现“生成报告”按钮。
3. 执行完成后页面出现 toast：“用例执行完成，可以查看报告”（不要求抽屉打开）。
4. 进入 “Allure报告” 页面：
   - 左侧展示历史报告列表（至少包含 runId 与时间信息）
   - 点击列表项，右侧加载对应 Allure 报告 iframe（与 `/api/runs/{runId}/allure-report/` 一致）
   - 支持 `?runId=xxx` 直达并自动选中

## 风险与兼容性

- 若运行环境缺少 `allure` CLI，后端 worker 可能无法生成 report zip，列表会缺少对应报告；需配合环境保证或在页面提供“生成/重试”的兜底入口。
- 当前 toast 组件不支持点击动作；本次仅按需求提供提示文案，不做“点击跳转”。

