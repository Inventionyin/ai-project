# WeiTesting 开发规范

本规范用于约束后续人工开发、AI 代码生成和代码评审。新增功能默认按本文执行；如因特殊情况偏离，需要在 PR 说明中写清原因、风险和补偿验证。

## 目标

- 保持后端、前端、脚本和文档的实现风格一致。
- 让功能交付同时包含接口、页面入口、权限、测试和验收证据。
- 防止临时凭证、调试绕过、生成物和一次性脚本混入正式代码。
- 让新人或 AI 接手时能先按规范查证，再开始修改。

## 通用原则

- 先读现有实现，再新增代码。优先复用本仓库已有 service、schema、API client、页面壳层和测试模式。
- 变更要有清晰边界。只修改当前任务需要的文件，不做无关重构、格式化或命名清理。
- 用户可见能力必须有入口。后端接口、前端页面、路由、侧栏、文档和测试要成套补齐。
- 高风险能力必须有诊断。外部系统、CI Token、插件沙箱、运维健康和性能基线都要能说明失败原因。
- 所有密钥只进入环境变量、GitHub Secrets 或部署平台密钥系统；不得写入源码、测试快照、截图、报告或 Markdown。

## 后端规范

### API 层

- 新接口放在 `ai-project-back-end/app/api/v1/endpoints/`，并在 `app/api/v1/__init__.py` 注册。
- 统一使用 `ApiResponse[T]` 响应包裹，返回 `code/message/data/requestId`。
- 路径命名沿用现有风格：
  - 项目内资源：`/api/projects/{projectId}/...`
  - 平台级能力：`/api/...`
- endpoint 只负责依赖注入、参数校验、调用 service 和事务收口；业务判断放到 service。
- 写操作必须在 endpoint 中处理 `commit/rollback`，参考现有 dashboard、integrations、devops endpoint。

### Schema 层

- 新响应类型放在 `app/schemas/<domain>.py`。
- 字段命名遵循现有前后端契约，API 响应可继续使用 camelCase。
- 状态枚举要显式定义，例如 `Literal["READY", "WARN", "BLOCKED"]`。
- 对外输出不得包含 token、secret、password、apiKey、webhook 明文。

### Service 层

- service 必须先做项目存在性和权限校验，优先复用已有 `_get_project` / `_require_project_read` 模式。
- 查询必须带 `tenant_id`，项目内数据必须同时带 `project_id`。
- 聚合型 service 要容忍部分配置缺失，用 `WARN/BLOCKED` 和 recommendation 说明，而不是直接吞异常或返回空白。
- 不允许用全局最近 N 条代替按实体查询最近记录，除非业务明确允许抽样。
- 外部系统联调默认区分：
  - 配置诊断：检查字段是否存在、格式是否合理。
  - 连通性 smoke：调用外部系统但不创建业务数据。
  - 业务闭环：创建/触发/清理真实对象，并保留回执。

## 前端规范

### API Client

- API client 放在 `ai-project_front_end/src/lib/api/`。
- 使用 `requestJson` 和 `authHeader`，不要在页面里直接拼 fetch。
- API client 负责兼容后端字段和状态值，页面只消费清洗后的类型。
- 时间字段进入页面前统一转为秒级时间戳或明确类型。

### 页面与路由

- 项目内页面统一使用 `createProjectShellPage` 包进 `AiTestingPlatformShell`。
- 新设置页需要同时补：
  - `src/router/index.ts`
  - `src/components/figma/ai-testing-platform/AiTestingSidebar.vue`
  - 对应 `src/views/settings/*.vue`
- 页面应优先展示可操作信息：状态、失败原因、指标、下一步、复制/刷新/导出动作。
- 运维、验收、配置类页面不要做营销式 hero；采用紧凑、可扫描的工作台布局。
- 页面必须处理 loading、error、empty 和 refresh 状态。

### UI 文案

- 页面标题使用业务名，例如“生产验收中心”“运维健康”“集成配置”。
- 状态文案要能指导行动：
  - `READY` -> 就绪/通过
  - `WARN` -> 预警/待确认
  - `BLOCKED` -> 阻塞/需处理
- 错误信息优先展示“哪一项失败、缺什么、下一步做什么”。

## 脚本规范

- 可重复执行的本地/CI/生产检查脚本放在 `scripts/`。
- 部署和运维脚本放在 `deploy/` 或 `ops/`。
- 脚本必须支持 dry-run 或明确说明会调用外部系统/产生真实业务数据。
- 脚本输出要适合 CI 阅读：成功、失败、跳过和警告要分清。

## 文档规范

- 生产、部署、外部系统、SLO、性能、Token 等专项内容放在 `docs/`。
- 新功能如果影响交付口径，需要同步更新相关文档或在 PR 中说明不需要更新。
- 文档要写“怎么执行”和“验收标准”，少写空泛背景。
- 已有专项文档优先引用，不重复复制整段内容。

## 代码评审清单

提交前至少自查：

- 是否有项目级权限和租户隔离。
- 是否无明文密钥、Token、Webhook、私钥。
- 是否有后端测试或前端 E2E 覆盖关键行为。
- 是否已更新路由、侧栏、文档和验收入口。
- 是否清理了 `dist/`、Playwright report、临时截图、日志等生成物。
- 是否运行了与变更匹配的验证命令，并在 PR 中写清结果。

## 相关文档

- CI 与外部 smoke：`docs/ci.md`
- 生产验收清单：`docs/PRODUCTION_ACCEPTANCE_CHECKLIST.md`
- 生产就绪：`docs/production-readiness.md`
- 外部系统联调：`docs/real-external-integrations.md`
- Token 治理：`docs/token-governance.md`
- 插件沙箱边界：`docs/plugin-sandbox-boundary.md`
- SLO：`docs/slo.md`
- 性能基线：`docs/performance-baseline.md`
