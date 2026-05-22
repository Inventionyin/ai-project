# WeiTesting PRD（最新版-代码对齐）

文档版本：v1.1（代码对齐）  
更新时间：2026-03-21  
文档范围：基于当前仓库 `ai-project_front_end` + `ai-project-back-end` 的已实现能力与已存在页面结构整理；同时给出下一阶段最小补齐清单（不包含纯设想功能）。

实现状态标记：
- 已落地：前后端均可闭环使用
- 后端已落地：后端能力存在，前端未接入或仅部分接入
- 前端占位/静态：前端页面或组件存在，但未与后端联动
- 未落地：前后端均未实现（仅保留为后续规划）

---

## 1. 背景与目标

### 1.1 背景
- 测试资产分散（用例、环境、接口定义、报告），执行与分析依赖人工、难以沉淀与复用。
- 需要一套统一平台，把“资产管理—执行—报告”形成最小闭环，并为后续 AI 能力接入预留结构。

### 1.2 当前版本目标（以 API 测试为核心）
- 覆盖多项目测试资产管理：项目、用例、套件、环境、接口集合。
- 打通最小可用执行链路：基于用例触发运行、查询运行与用例子结果、生成并查看 Allure 报告。
- 建立统一接口约定：统一响应结构、错误码、分页、鉴权、幂等键。
- 预留扩展：Worker 协议（注册/心跳/拉取/上报）与 AI 导入任务（ai-import）用于后续能力演进。

---

## 2. 范围与边界

### 2.1 已落地（可用闭环）
- 账号体系：注册、登录、退出、获取当前用户。
- 项目管理：项目列表分页、创建、编辑、删除、项目详情、项目首页统计。
- 仪表盘：summary / failure-top / trend / quality-gate（展示型门禁）。
- 用例管理：列表筛选分页、创建、详情、编辑、删除、维护人选项、版本列表、版本回滚。
- 套件管理：套件 CRUD、套件项查询、套件项批量写入（编排保存能力后端已具备）。
- 环境管理：环境 CRUD（后端完备；前端独立页面仍占位）。
- 执行（Runs）：创建/列表/详情/取消/重试、子用例运行分页、幂等键、Allure 报告生成与浏览。
- 接口集合（Collections）：集合 CRUD、分组 CRUD/排序、请求 CRUD、导入/导出、集合/单请求快速运行。
- API Targets：接口目标 CRUD（用于绑定时选择目标 baseUrl 等）。
- 用例绑定（Testcase Bindings）：对单用例配置多套执行绑定（target/dataset/params/优先级/启用）。
- Worker 协议：worker register/heartbeat/poll/report（用于“执行资源”接入）。
- AI 导入（ai-import）：导入任务创建、上传文件、查询任务与预览项。

### 2.2 部分落地（需补齐联调/UI）
- 运行记录页：前端存在页面结构，但主列表仍为静态数据，需对接后端 runs 列表与操作。
- 运行详情页：路由占位，需实现 run 详情与 case-runs 展示，并复用 Allure 报告入口。
- 套件编排页：已接入“读取编排项”，但“用例池数据/保存动作”存在未完全接入的情况（以实际页面实现为准）。
- 接口集合详情页：路由占位；列表与创建等已有接入，但详情编辑/导入导出/运行等需补齐 UI。
- 环境管理页：路由占位；后端 environments 已完整，需补齐 CRUD UI。
- Worker 管理页：前端为静态展示；后端已有 worker 协议，但缺少“管理端查询 workers 列表/状态”的只读 API。
- 报告中心：前端组件存在，但未数据化；当前平台的可用报告以 Allure 为主（挂载在 runs 下）。
- 测试数据集：前端存在本地交互页面，但后端未提供 datasets 独立模块；目前仅在 binding 中保留 datasetId/datasetName 字段。

### 2.3 非范围（本期不做）
- UI 自动化执行编排与结果接入（仅保留 Worker 扩展入口）。
- AI 生成用例/失败归因（当前仅包含 ai-import 导入与预览，不包含 LLM 生成链路）。
- 成员/权限管理 UI、审计日志 UI、集成配置 UI（路由占位，后端也未形成完整业务 API）。

---

## 3. 目标用户与角色

### 3.1 角色
- 管理员（Admin）：系统级配置与跨项目高权限（当前以角色字段保留，未形成完整 UI）。
- 项目负责人（Owner）：项目级管理权限。
- 编辑者（Editor）：可编辑测试资产、配置执行。
- 查看者（Viewer）：只读查看。

### 3.2 鉴权与租户原则（后端已实现）
- 接口默认鉴权，除 `/health`、`/api/auth/login`、`/api/auth/register` 外均需身份。
- 支持两种身份透传方式：
  - `Authorization: Bearer <jwt>`：JWT 中包含 `user_id / tenant_id / roles`。
  - 网关透传：`X-User-Id` + `X-Tenant-Id`（可选 `X-Roles`，逗号分隔）。
- 所有业务数据以 `tenant_id` 做隔离与校验（后端服务层普遍以 CurrentUser.tenant_id 作为过滤条件）。

---

## 4. 典型使用流程（当前版本可闭环）

### 4.1 从登录到资产管理
1. 用户注册/登录获取 `accessToken`。
2. 进入项目列表，创建或选择项目。
3. 在项目内创建测试用例（支持 Markdown 内容与 API 元信息字段）。
4. 创建套件，并将用例编排到套件中（读取与保存能力后端具备）。
5. 创建环境（baseUrl/变量/密钥），用于后续执行绑定或运行时选择。

### 4.2 从用例到执行与报告
1. 为用例创建执行绑定（选择 apiTarget、配置 params、启用/优先级等）。
2. 发起批量执行（两条路径均已落地）：
   - 通过 bindings 执行：`POST /api/runs/from-testcases`
   - 直接 HTTP 执行（不依赖 bindings）：`POST /api/runs/from-testcases-http`
3. 轮询 `GET /api/runs/{runId}` 与 `GET /api/runs/{runId}/case-runs` 获取执行进度与子用例结果。
4. 执行结束后，生成 Allure 报告：`POST /api/runs/{runId}/allure-report/generate`。
5. 浏览报告：`GET /api/runs/{runId}/allure-report/`（支持 `access_token` query 透传以便 iframe 使用）。

---

## 5. 功能需求（模块级，代码对齐）

### 5.1 认证与账号（已落地）
- 后端接口：
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
- 前端现状：登录/注册/退出/用户信息均已接入。

### 5.2 项目管理（已落地）
- 功能范围：
  - 项目列表分页、创建、编辑、删除、项目详情查询、首页聚合统计。
- 后端接口：
  - `GET /api/projects`
  - `POST /api/projects`
  - `GET /api/projects/{id}`
  - `PUT /api/projects/{id}`（同时兼容 `PUT /api/projects?id=...`）
  - `DELETE /api/projects/{id}`（同时兼容 `DELETE /api/projects?id=...`）
  - `GET /api/projects/home-stats`

### 5.3 仪表盘（已落地）
- 功能范围：汇总指标、失败 Top、趋势图、质量门禁（展示）。
- 后端接口：
  - `GET /api/projects/{projectId}/dashboard/summary`
  - `GET /api/projects/{projectId}/dashboard/failure-top`
  - `GET /api/projects/{projectId}/dashboard/trend`
  - `GET /api/projects/{projectId}/dashboard/quality-gate`
- 前端现状：仪表盘页面已接入并渲染。

### 5.4 用例管理（已落地）
- 功能范围：
  - 列表分页与筛选（title/type/status/tag/ownerId）
  - 创建/详情/编辑/删除
  - 版本列表与回滚
  - 维护人选项查询
- 后端接口：
  - `POST /api/testcases`
  - `GET /api/testcases`
  - `GET /api/testcases/owners`
  - `GET /api/testcases/{id}`
  - `PUT /api/testcases/{id}`（同时兼容 `PUT /api/testcases?id=...`）
  - `DELETE /api/testcases/{id}`
  - `GET /api/testcases/{id}/versions`
  - `POST /api/testcases/{id}/restore`
- 字段说明（后端已支持）：
  - 基础：title/type/priority/status/tags/ownerId/contentMd/version
  - AI/接口元信息：feature、apiMethod、apiUrl、apiParams、apiHeaders、expectedResult

### 5.5 用例绑定（Testcase Bindings）（后端已落地，前端已封装 API）
- 目标：为同一用例配置多套“执行绑定”（不同环境目标、不同参数、不同数据集引用）。
- 后端接口：
  - `GET /api/testcases/{testcaseId}/bindings`
  - `POST /api/testcases/{testcaseId}/bindings`
  - `PUT /api/testcase-bindings/{bindingId}`
  - `DELETE /api/testcase-bindings/{bindingId}`
- 关键字段：
  - apiTargetId（指向 API Target）
  - datasetId/datasetName（数据集引用占位）
  - params（覆盖参数）
  - priority/enabled/version

### 5.6 测试套件（已落地；前端编排能力需继续对齐）
- 功能范围：
  - 套件 CRUD
  - 套件项获取与批量写入（编排保存）
- 后端接口：
  - `POST /api/suites`
  - `GET /api/suites`
  - `GET /api/suites/{id}`
  - `PUT /api/suites/{id}`
  - `DELETE /api/suites/{id}`
  - `GET /api/suites/{suiteId}/items`
  - `POST /api/suites/{suiteId}/items`

### 5.7 环境管理（后端已落地，前端页面占位）
- 功能范围：环境 CRUD（name/baseUrl/variables/secrets/healthCheck 等）。
- 后端接口：
  - `POST /api/projects/{projectId}/environments`
  - `GET /api/projects/{projectId}/environments`
  - `GET /api/projects/{projectId}/environments/{envId}`
  - `PUT /api/projects/{projectId}/environments/{envId}`
  - `DELETE /api/projects/{projectId}/environments/{envId}`

### 5.8 执行与运行记录（后端已落地；前端部分联调）
- 功能范围（后端能力）：
  - 创建运行（支持 Idempotency-Key）
  - 运行列表分页查询（projectId/status/from/to）
  - 运行详情查询（含 progress）
  - 子用例运行分页（case-runs，可按 status 过滤）
  - 取消、重试（可选择 failedOnly）
  - 生成并挂载 Allure 报告（zip 入库为 artifact，提供静态资源访问）
- 后端接口：
  - `POST /api/runs`
  - `GET /api/runs`
  - `GET /api/runs/{runId}`
  - `GET /api/runs/{runId}/case-runs`
  - `POST /api/runs/{runId}/cancel`
  - `POST /api/runs/{runId}/retry`
  - `POST /api/runs/from-testcases`
  - `POST /api/runs/from-testcases-http`
  - `POST /api/runs/{runId}/allure-report/generate`
  - `GET /api/runs/{runId}/allure-report/*`（schema 隐藏，用于报告静态资源）
- 前端现状：
  - 用例页已接入批量执行（from-testcases-http）与 Allure 报告展示面板。
  - 运行记录列表页与运行详情页仍需按上述接口补齐联调。

### 5.9 接口集合（Collections）（后端已落地；前端列表/创建已接入，详情页占位）
- 功能范围（后端能力）：
  - 集合 CRUD
  - 分组 CRUD/排序
  - 请求 CRUD
  - 导入/导出
  - 集合/单请求快速运行
- 后端接口（节选）：
  - `GET/POST /api/collections`
  - `GET/PUT/DELETE /api/collections/{collectionId}`
  - `POST/PUT/DELETE /api/collections/{collectionId}/groups*`
  - `POST/GET/PUT/DELETE /api/collections/{collectionId}/requests*`
  - `POST /api/collections/import`
  - `GET /api/collections/{collectionId}/export`
  - `POST /api/collections/{collectionId}/run`
  - `POST /api/collections/{collectionId}/requests/{requestId}/run`
- 前端现状：集合列表与创建能力已接入；集合详情编辑/运行/导入导出需补齐 UI 与联调。

### 5.10 API Targets（后端已落地；前端已封装 API）
- 目标：统一管理“执行目标 baseUrl/描述/启用/默认”等，用于 bindings 或请求运行时选择。
- 后端接口：
  - `GET /api/api-targets`
  - `POST /api/api-targets`
  - `PUT /api/api-targets/{id}`
  - `DELETE /api/api-targets/{id}`

### 5.11 Worker 协议（后端已落地；前端管理页静态）
- 定位：执行资源对接入口（worker 主动拉取任务与上报结果）。
- 后端接口：
  - `POST /api/workers/register`（要求 `X-Tenant-Id`，返回 worker token）
  - `POST /api/workers/heartbeat`（worker token 鉴权）
  - `POST /api/workers/poll`（worker token 鉴权）
  - `POST /api/workers/report`（worker token 鉴权）
- 当前缺口：
  - 缺少“管理端查询 workers 列表/状态/最近心跳”的只读 API（建议新增 `/api/workers` GET 等）。

### 5.12 AI 导入（ai-import）（后端已落地；前端需按产品设计接入）
- 目标：把外部文档/文件导入为“候选用例预览项”，支持后续选择入库（本期仅到预览层）。
- 后端接口：
  - `POST /api/testcases/ai-import/jobs`（支持 Idempotency-Key）
  - `POST /api/testcases/ai-import/jobs/{jobId}/file`（multipart 上传）
  - `GET /api/testcases/ai-import/jobs/{jobId}`（返回 summary 与 previewItems）

---

## 6. 前端信息架构与页面现状

### 6.1 已接入后端的核心页面
- `/login`、`/register`：登录注册闭环
- `/projects`：项目列表/创建/编辑/删除 + 首页统计
- `/projects/:projectId/dashboard`：仪表盘 4 个接口 + 最近 runs
- `/projects/:projectId/assets/testcases`、`/projects/:projectId/assets/testcases/:id`：用例 CRUD + owners + 批量执行（from-testcases-http）+ Allure 面板
- `/projects/:projectId/assets/suites`、`/projects/:projectId/assets/suites/:id`：套件列表/创建 + 套件项读取
- `/projects/:projectId/assets/apis`：接口集合列表/创建/分组/请求创建（详情页尚未对齐）

### 6.2 静态或占位页面（需补齐联调）
- `/projects/:projectId/runs`：运行记录列表（需对接 `/api/runs`）
- `/projects/:projectId/runs/:runId`：运行详情（占位）
- `/projects/:projectId/reports`：报告中心（未数据化）
- `/projects/:projectId/workers`：Worker 管理（静态）
- `/projects/:projectId/assets/data`：测试数据（静态，本地交互）
- `/projects/:projectId/settings/environments`：环境管理（占位，需对接 environments CRUD）
- `/settings/integrations`、`/settings/rbac`、`/settings/audit`：占位

---

## 7. 统一技术与接口约定（后端已实现）

### 7.1 统一响应结构
```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "requestId": "req_xxx"
}
```

说明：
- 后端异常统一返回 HTTP 200，但通过 `code` 表达业务错误。
- `requestId` 来自 `X-Request-Id`（或 `X-RequestId`），若未传入则后端生成。

### 7.2 分页结构
```json
{
  "page": 1,
  "pageSize": 20,
  "total": 100,
  "items": []
}
```

### 7.3 鉴权机制
- 优先：`Authorization: Bearer <accessToken>`
- 备选：`X-User-Id` + `X-Tenant-Id`（可选 `X-Roles`）

### 7.4 幂等键（Idempotency-Key）
- 部分创建接口支持 `Idempotency-Key` 头（最大 128 字符），用于避免重复提交导致重复创建。

### 7.5 错误码映射（后端统一异常映射）
- 0：成功
- 40001：参数校验失败（含 400 / 422）
- 40101：未登录或 token 无效
- 40301：无权限
- 40401：资源不存在
- 40501：方法不允许
- 40901：冲突（如版本冲突/幂等等）
- 42901：请求过频
- 50301：依赖不可用（数据库等）
- 50001：服务内部错误

---

## 8. 数据模型（核心实体，面向联调）

### 8.1 项目域
- Project：id / tenantId / name / description / ownerId / createdAt / updatedAt + 聚合字段（home-stats）。
- Environment：id / projectId / name / baseUrl / variables / secrets / healthCheck（后端支持）。
- ApiTarget：id / projectId / name / baseUrl / isDefault / enabled / version / timestamps。

### 8.2 用例域
- TestCase：id / projectId / title / type / priority / status / tags / ownerId / contentMd / version（v1.x 格式） + api 元信息字段。
- TestCaseVersion：testcaseId + version + snapshot（用于版本列表/回滚）。
- TestcaseBinding：id / testcaseId / apiTargetId / datasetId/datasetName / params / enabled / priority / version。

### 8.3 套件域
- Suite：id / projectId / name / description / defaultEnvId / config（json） / timestamps。
- SuiteItem：suiteId / testcaseId / orderNo / params + testcase 展示字段（用于编排）。

### 8.4 执行域
- Run：id / projectId / suiteId? / envId? / triggerType / status / progress / summary。
- CaseRun：id / runId / testcaseId / status / startAt/endAt / errorType/errorMessage。
- Artifact：runId / caseRunId? / type / storage_url / size / meta_json（Allure report 以 LOG_BUNDLE + meta.kind=ALLURE_REPORT 存储）。

### 8.5 Worker 域
- Worker：id / tenantId / token_hash / capabilities / slots / status / last_seen_at / version（执行侧使用）。

### 8.6 AI Import 域
- AiImportJob：jobId / projectId / sourceType / status / summary / previewItems[]（可选中）。

---

## 9. 验收标准（按当前版本目标）

### 9.1 已落地验收项
- 登录注册：登录成功可进入项目页，鉴权失效会退出并回登录。
- 项目：项目创建/编辑/删除可落库并刷新列表；home-stats 可正常展示。
- 仪表盘：summary/failure-top/trend/quality-gate 可正常渲染。
- 用例：列表/详情/创建/编辑/删除闭环；owners 选项可用；版本列表与回滚可用。
- 套件：套件列表/创建闭环；可读取套件项；后端可保存套件项。
- 执行：可创建 runs（含 from-testcases(-http)）；可查询 run 与 case-runs；可取消与重试；可生成并访问 Allure 报告。
- 集合：collections CRUD + group/request CRUD + import/export/run 接口可用。

### 9.2 下一阶段验收项（最小补齐清单）
- 运行记录页：接入 `/api/runs` 列表与筛选，支持取消/重试并刷新状态。
- 运行详情页：接入 `/api/runs/{runId}` + `/case-runs`，展示进度、失败原因，并提供 Allure 报告入口。
- 环境管理页：补齐 environments CRUD UI，并用于批量执行选择环境。
- 接口集合详情页：补齐集合详情编辑、导入导出、运行与结果展示 UI。
- Worker 管理：补齐管理端查询 API（workers list/状态），页面从静态改为真实数据。
- 测试数据集：补齐后端 datasets 模块与前端接入（或明确本期继续保留占位策略）。

---

## 10. 迭代优先级建议（以“可用闭环 + 提升覆盖”为导向）

### P0（必须）
- Runs 列表页真实联调（列表/筛选/取消/重试）
- Runs 详情页真实联调（详情/case-runs/报告入口）
- 环境管理页补齐 CRUD UI（后端已完备）

### P1（高优先）
- 套件编排页：用例池接入 `GET /api/testcases` + 编排保存接入 `POST /api/suites/{suiteId}/items`
- 接口集合详情页补齐（编辑/运行/导入导出）

### P2（中优先）
- Worker 管理：补齐管理端 API + 页面联动
- 测试数据集：落后端模块与绑定联动
- 报告中心数据化（在 Allure 之外提供平台聚合视图）

