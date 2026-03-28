# AI 测试平台 PRD（可执行版）

## 1. 背景与目标

背景 ：团队测试资产分散（用例、脚本、数据、报告、环境配置），测试执行与分析依赖人工；AI 能力无法规模化落地到“生成-执行-分析-回归”闭环。
产品目标 ：建设一套 AI 测试平台，覆盖测试资产管理、用例/脚本生成、测试执行编排、结果分析与报告、缺陷联动与质量度量。
核心指标（OKR） ：

- 用例产出效率提升：同等需求下用例编写工时降低 ≥40%
- 回归效率提升：自动化回归覆盖率提升 ≥30%（按关键路径）
- 报告产出时效：执行完成后 5 分钟内生成可分享报告
- 线上缺陷逃逸率下降：关键模块下降 ≥20%

## 2. 范围与边界

本期（V1）范围 （MVP 可落地）：

- 多项目/多环境的测试管理
- 资产中心：用例、测试套件、接口定义（核心）、测试数据（文件管理）、UI 页面对象（可选）
- AI 能力：用例生成（基于接口定义）、断言/检查点建议（仅单接口）
- 执行中心：任务编排、并发执行、日志/产物归档（仅API测试，UI测试延后至V1.1）
- 报告中心：可视化报告、趋势（简单折线）、质量门禁（仅展示，不做自动阻断）
- 权限/审计、通知（至少支持一种，如飞书/企微）
- 开放 API：可被 CI/CD 调用触发执行并回传结果

非范围（V1 不做或弱化） ：

- 自研浏览器/设备云（可对接第三方）
- 复杂需求管理系统替代（仅做轻量需求条目/引用）
- AI 自动“直接修复代码并提交”默认不开启（可作为 V2）
- 失败归因分析（V1 仅做错误日志聚合，归因能力延后至 V1.2）
- UI 自动化执行（V1 不做，但 Worker 需预留扩展能力）

## 3. 目标用户与角色

- 测试工程师 ：管理用例/套件、配置执行任务、分析报告
- 测试开发/自动化工程师 ：维护脚本与框架适配、执行资源与 Worker
- 开发工程师 ：查看失败归因、定位日志、快速复现
- QA 负责人/管理者 ：查看质量看板、趋势、门禁与发布决策
- 管理员 ：租户/组织、权限、集成配置（IM/邮箱/CI/缺陷系统）

## 4. 典型使用流程（端到端）

1. 创建项目与环境（dev/staging/prod），配置变量与密钥（加密存储）
2. 导入接口集合（Swagger/Postman）或编写接口用例，建立测试套件
3. 选择接口定义 → AI 生成单接口用例草稿（含常见断言） → 人工确认并入库
4. 创建执行计划：选择套件、环境、并发、触发方式（手动/定时/CI）
5. 平台分发任务到 Worker 执行 → 实时日志 → 产物入库（请求/响应、断言明细）
6. 执行完成后生成报告与趋势，必要时推送通知并创建缺陷（对接 Jira/禅道等）

## 5. 功能需求（模块级）

### 5.1 项目与环境

- 项目：名称、描述、负责人、成员、标签
- 环境：baseUrl、DB/服务地址、变量集、密钥（KMS/加密字段）、可用性探测
- 变量优先级：环境变量 > 套件变量 > 用例变量 > 全局变量
- 环境健康检查：HTTP 探测/DB 连通/关键依赖探测（可选）

### 5.2 资产中心

**用例（TestCase）**

- 字段：标题、前置条件、步骤、期望结果、标签、优先级、类型（接口/UI/性能/混合）、维护人、版本、**自动化脚本/断言（直接关联接口请求或UI元素）**
- 支持：Markdown 编辑、历史版本、评审状态（草稿/已评审/已弃用）
- 与需求条目关联（可选）：storyId/需求链接
- **校验规则：标题长度1-100，类型枚举（API/UI/PERF/MIX），优先级枚举（P0/P1/P2/P3）**

**套件（Suite）**

- 套件内用例排序、分组、参数化、失败重试策略、依赖关系（可选）
- 运行配置：超时、并发、是否阻塞（fail-fast）
- **配置面板支持“从数据集导入参数”快捷操作**

**测试数据（TestData）**

- 数据集：CSV/JSON，支持变量引用与脱敏展示（V1仅做文件管理）
- 数据生成（可选）：基于规则或 AI 生成（仅入库草稿，V1不做）

**接口集合（API Collection）**

- 类 Postman：分组、请求、变量、断言模板、鉴权配置（Bearer/Basic/签名）
- 断言：状态码、JSONPath、Schema、响应时间阈值
- **支持导入（Postman/Swagger）和导出为代码（如curl）**
- **断言模板预置常见校验（状态码、关键字段存在性）**

**UI 自动化资产**

- 脚本仓库引用（Git URL + 分支 + Path）或平台内脚本（V1 建议仅做引用，不编辑）

### 5.3 AI 助手（可控、可回溯）

- 输入：接口定义（必须）、需求描述（可选）、历史用例（可选）
- 输出能力（V1.1）：
  - 用例生成：基于接口定义生成单接口用例草稿（含正向、边界、异常场景）
  - 断言建议：基于响应结构给出常用断言（状态码、字段非空、类型校验）
- 约束：
  - 所有 AI 输出必须可追溯：保存 prompt、上下文引用、模型版本、生成时间
  - 支持“人工确认后入库/入套件”，默认不自动覆盖原资产
  - **Prompt模板需业务方确认，避免包含敏感信息**

### 5.4 执行中心（任务编排）

- 执行任务（Run）：一次触发产生一个 Run，包含多个 Job/CaseRun
- 触发方式：手动、定时（Cron）、Webhook/CI 调用
- 执行资源：
  - Worker 注册（token），心跳，能力标签（api/perf），并发槽位
  - 队列调度：按项目优先级、环境、标签路由（可用 Redis Stream 或 Kafka）
- 执行产物：
  - API：请求/响应（脱敏）、断言明细
  - **存储路径规范：`{tenant}/{project}/runs/{runId}/{caseRunId}/`**
  - **支持调试模式：用户单次运行用例，不经过调度，直接返回结果**

### 5.5 报告与看板

- 单次报告：总览、失败列表、按模块/标签统计、关键日志直达
- 趋势：按时间维度通过率、失败Top、用例不稳定率（flake，定义：失败次数>1且通过次数>0的用例占比）
- 质量门禁（仅展示）：通过率阈值、关键用例必须通过、性能阈值（V1不自动阻断）
- 导出与分享：链接、PDF（可选）、对外只读访问（token）

### 5.6 缺陷与通知集成

- 缺陷：支持对接 Jira/禅道/飞书多维表格（至少一种），**支持多实例配置（不同项目可对接不同地址）**
- 通知：邮件/企业微信/飞书（至少一种），**优先实现Webhook自定义，允许用户填写任意URL**
- 规则：仅失败、失败+不稳定、门禁失败、超时等

### 5.7 权限与审计

- 组织/租户（必须）：Tenant -> Project -> Resources，**所有表必须带 tenant_id，API层自动注入**
- RBAC：
  - Admin：全局配置与集成
  - Owner：项目管理、成员管理
  - Editor：资产编辑、执行配置
  - Viewer：只读（可额外授权“触发执行”）
- 审计：关键操作（删除/导出/密钥变更/集成变更）留痕

## 6. 前端 UI（信息架构与页面）

导航结构

- 仪表盘
- 资产中心（用例/套件/接口/数据/UI脚本）
- 执行中心（运行记录/计划任务/Worker）
- 报告中心（单次报告/趋势看板）
- 集成与设置（通知/缺陷/CI/Webhook/权限）

关键页面

1. 仪表盘：今日执行、近7天趋势、失败Top、门禁状态
2. 用例列表：过滤（标签/模块/类型/状态）、批量操作、版本查看
3. 用例详情：步骤、期望、关联套件、历史运行、AI 生成/改写入口
4. 套件编排：拖拽排序、参数与变量、重试/超时策略
5. 执行创建：选择套件+环境+并发+触发方式+通知规则
6. 运行详情：实时日志流、用例树、失败定位（请求/响应）
7. 报告详情：结论、统计、失败归因（V1仅展示错误信息）、缺陷创建按钮
8. Worker 管理：在线状态、能力、版本、最近心跳、并发槽位

## 7. 后端服务与 API（概要设计）

服务划分（可单体起步，结构按模块分层）

- Auth/RBAC
- Asset Service（cases/suites/collections/data）
- Run Service（runs/jobs/results/artifacts）
- AI Service（prompt、生成记录、归因任务，V1.1启用）
- Integration Service（webhook、issue、notify）
- Worker Gateway（任务拉取/上报）

API 设计（REST 示例，V1 必须）

- 认证
  - POST /api/auth/login （可用 SSO 作为 V2）
  - GET /api/auth/me
- 项目/环境
  - POST /api/projects
  - GET /api/projects/{id}
  - POST /api/projects/{id}/environments
- 用例/套件
  - POST /api/testcases
  - GET /api/testcases?projectId=&tag=&type=&status=
  - GET /api/testcases/{id}
  - POST /api/suites
  - POST /api/suites/{id}/items （编排用例）
- 执行
  - POST /api/runs （创建并触发）
  - GET /api/runs?projectId=&status=&from=&to=
  - GET /api/runs/{id} （含实时状态）
  - GET /api/runs/{id}/artifacts/{artifactId} （下载/预览）
  - **POST /api/runs/debug （调试模式：直接执行单个用例，返回结果）**
- Worker
  - POST /api/workers/register
  - POST /api/workers/heartbeat
  - POST /api/workers/poll （拉取任务）
  - POST /api/workers/report （上报结果/产物索引）
- AI（V1.1）
  - POST /api/ai/generate-testcases
  - POST /api/ai/analyze-run/{runId}
  - GET /api/ai/records?entityType=&entityId=
- 集成
  - POST /api/integrations/issue （创建缺陷）
  - POST /api/integrations/notify/test （测试通知）

关键约定

- 统一返回： { code, message, data, requestId }
- 分页： page,pageSize,total,items
- 幂等： POST /api/runs 支持 Idempotency-Key

## 8. 数据库设计（核心表） 建议：PostgreSQL/MySQL 均可；产物（截图/视频/trace）放对象存储（MinIO/S3），DB 存索引与元数据。

### 8.1 基础与权限

- tenants ：id, name, created_at
- users ：id, tenant_id, email, name, status, created_at
- projects ：id, tenant_id, name, owner_id, created_at
- project_members ：project_id, user_id, role
- environments ：id, project_id, name, base_url, variables_json, secrets_ref（可指向外部密钥服务）, health_config_json

### 8.2 资产

- testcases ：id, project_id, title, type, priority, status, content_md, tags_json, version, created_by, updated_at
- testcase_versions ：id, testcase_id, version, content_md, created_by, created_at
- suites ：id, project_id, name, config_json, created_by, updated_at
- suite_items ：id, suite_id, testcase_id, order_no, params_json
- api_collections ：id, project_id, name, variables_json
- api_requests ：id, collection_id, name, method, url, headers_json, body_json, asserts_json
- test_data_sets ：id, project_id, name, type, content_blob_ref, schema_json

### 8.3 执行与产物

- runs ：id, project_id, suite_id, env_id, trigger_type, status, start_at, end_at, summary_json, created_by
- jobs ：id, run_id, worker_id, status, start_at, end_at, meta_json
- case_runs ：id, run_id, testcase_id, status, start_at, end_at, error_type, error_message, metrics_json
- artifacts ：id, run_id, case_run_id, type, storage_url, **size**, meta_json, created_at
- workers ：id, tenant_id, name, token_hash, capabilities_json, slots, status, last_seen_at, version

### 8.4 AI 与集成

- ai_records ：id, project_id, entity_type, entity_id, model, prompt, context_refs_json, output_json, created_by, created_at
- issue_links ：id, run_id, case_run_id, provider, issue_key, url, created_at
- notifications ：id, project_id, channel, target, rule_json, enabled, created_at
- audit_logs ：id, tenant_id, user_id, action, resource_type, resource_id, detail_json, created_at

索引建议

- runs(project_id, start_at desc) , case_runs(run_id, status) , testcases(project_id, updated_at desc)
- workers(tenant_id, last_seen_at desc)

## 9. 非功能需求（NFR）

- 性能：列表页 P95 < 800ms（常用查询走索引）；Run 详情实时刷新 2s/次
- 可用性：平台 99.5%（V1 目标）；Worker 断连自动重试/任务回收
- 安全：
  - 密钥不落日志；加密存储；访问控制最小权限
  - 产物链接带时效签名；对外分享只读 token 可撤销
  - **API请求/响应脱敏（手机号、身份证等按规则掩码）**
- 可观测：请求级 requestId，关键链路指标（Run 创建、调度、完成耗时）
- 合规：审计日志保留期可配置（默认 180 天）

## 10. 里程碑（建议按迭代交付）

- **V1-MVP（3个月）**：项目/环境、用例/套件（仅接口类型）、执行中心（仅API测试）、报告（单次+简单趋势）、基础RBAC、Webhook触发、飞书/企微通知
- **V1.1（+2个月）**：AI用例生成（基于接口定义）、Jira集成、趋势看板增强、UI执行（Playwright）
- **V1.2（+2个月）**：数据集管理、失败归因（初版，错误聚类+人工标签）、质量门禁（自动阻断）

## 11. 验收标准（可测试）

- 资产：可创建/查询/版本化用例与套件；支持按标签/类型筛选；**字段校验符合规则**
- 执行：可手动与 API 触发 Run；可查看实时日志与最终报告；产物可下载/预览；**调试模式可用**
- AI：生成用例可一键保存为草稿；**生成记录可追溯**
- 权限：Viewer 不能编辑资产；Editor 不能改项目成员；审计可查删除记录；**跨租户数据隔离**
- 集成：配置通知后，Run 失败能推送到指定渠道；可从失败用例创建缺陷并回链

## 12. 默认技术选型（可落地建议）

- 前端：React + Ant Design（或同类），WebSocket/SSE 用于实时日志
- 后端：Node.js/NestJS 或 Java/Spring Boot（任选其一），REST + Webhook
- DB：PostgreSQL/MySQL；缓存与队列：Redis（任务队列可选）
- 对象存储：MinIO/S3（存 artifacts）
- Worker：容器化部署（Docker/K8s），支持 API 执行器（V1），预留插件化接口

## 13. 信息架构与路由（前端可直接开工）

- /login 登录
- /projects 项目列表/创建
- /projects/:projectId/dashboard 仪表盘
- /projects/:projectId/assets/testcases 用例列表
- /projects/:projectId/assets/testcases/:id 用例详情/编辑
- /projects/:projectId/assets/suites 套件列表
- /projects/:projectId/assets/suites/:id 套件编排
- /projects/:projectId/assets/apis 接口集合
- /projects/:projectId/assets/apis/:id 接口集合详情
- /projects/:projectId/assets/data 数据集
- /projects/:projectId/runs 运行记录
- /projects/:projectId/runs/:runId 运行详情（实时）
- /projects/:projectId/reports 报告中心（单次/趋势）
- /projects/:projectId/settings/environments 环境管理
- /settings/integrations 集成配置（管理员/Owner）
- /settings/rbac 权限与成员
- /settings/audit 审计日志

## 14. 前端页面规格（字段级，可直接画 UI/写接口联调）

### 14.1 登录页

组件

- 输入框：邮箱/用户名、密码
- 按钮：登录
- 错误提示：toast + 表单项红字
  交互
- 登录成功跳转最近访问项目；无则 /projects
- 登录失败展示错误码对应文案（见错误码字典）

### 14.2 项目列表 /projects

列表列

- 项目名（可点击）
- Owner
- 成员数
- 最近运行时间
- 创建时间
- 操作：进入/设置（Owner/Admin）
  顶部操作
- 新建项目（Owner/Admin）
- 搜索：项目名
- 筛选：我的项目（成员包含我）
  新建项目弹窗字段
- name（必填，2-50）
- description（可选，0-200）
- ownerId（默认当前用户）

### 14.3 仪表盘 /projects/:projectId/dashboard

卡片

- 今日执行：runs 总数、通过率、失败数、进行中数
- 近7天趋势折线：通过率、失败数
- 失败 Top10：用例/套件维度切换
- 质量门禁状态（可选 V1.1）：最近一次门禁结果
  数据刷新
- 每 60s 刷新一次
- “进行中” run 显示实时状态（轮询 5s 或 SSE）

### 14.4 用例列表 /assets/testcases

列表列（默认）

- 标题（点击进入详情）
- 类型：API/UI/PERF/MIX
- 优先级：P0/P1/P2/P3
- 状态：草稿/已评审/已弃用
- 标签（tag chip）
- 维护人
- 最近更新
- 最近运行结果（pass/fail/skip/none）可选
- 操作：编辑/复制/弃用/删除（按权限）
  筛选区
- 关键词：标题
- 标签多选
- 类型多选
- 状态多选
- 维护人
- 更新时间范围
  批量操作
- 批量打标签
- 批量加入套件（选择套件 + 插入位置：末尾/指定序号）
- 批量弃用/删除（删除需要二次确认 + 审计）
  空态
- 无用例：提供“AI 生成用例”“新建用例”“导入接口集合”

### 14.5 用例详情/编辑 /assets/testcases/:id

分区

1. 基本信息（表单）

- title（必填）
- type（必填）
- priority（必填）
- status（必填）
- tags（可选，多值）
- owner（可选）
- linkedRequirement（可选：URL/ID）

1. 内容（Markdown 编辑器）

- 前置条件
- 步骤（建议用有序列表）
- 期望结果
- 备注（可选）

1. AI 辅助（右侧栏或上方 tab）

- 生成用例：输入接口集合/选择接口，生成单接口用例草稿
- 改写/补全：补边界、补异常（V1.1）
- 一键对比：AI 生成草稿 vs 当前内容（diff 视图）
- 操作：采纳（写入草稿）/复制到剪贴板

1. 历史运行（tab）

- 最近 20 次 case_run 列表：runId、状态、耗时、失败原因、时间
- 点击进入 run 详情并定位该用例节点
  保存策略
- 支持草稿保存
- 发布/评审通过：status 变为已评审（可选审批流 V1.1）

### 14.6 套件列表 /assets/suites

列表列

- 套件名
- 用例数
- 默认环境（可选）
- 配置摘要（并发/超时/重试）
- 最近运行
- 维护人
- 操作：编排/运行/复制/删除
  新建套件字段
- name（必填）
- description（可选）
- defaultEnvId（可选）
- config（默认值见 18 节）

### 14.7 套件编排 /assets/suites/:id

左侧：用例池

- 搜索/筛选同用例列表
- 支持拖拽加入右侧编排区
  右侧：套件内容（树/列表）
- 列：顺序、标题、类型、参数（有则展示徽标）
- 操作：上移/下移/删除/设置参数
  套件配置（折叠面板）
- timeoutSec（默认 600）
- concurrency（默认 4）
- retryCount（默认 1）
- retryOnlyOn（flake/network/timeout）
- failFast（默认 false）
- variables（key/value）
- notificationsRuleId（可选）

### 14.8 接口集合 /assets/apis

列表列

- 集合名
- 请求数
- 最近更新
- 操作：进入/导入/导出/删除
  集合详情
- 左侧：分组/请求树
- 中间：请求编辑（method/url/headers/body/auth）
- 右侧：断言模板（状态码、JSONPath、schema、响应时间阈值）
- 顶部：运行（选择环境、并发、循环次数）

### 14.9 运行记录 /runs

列表列

- Run ID（短码展示）
- 触发方式：手动/定时/CI
- 套件名
- 环境
- 状态：queued/running/passed/failed/canceled
- 通过率（完成后）
- 开始/结束/耗时
- 创建人
- 操作：查看/重跑/取消（running 可取消）
  筛选
- 状态、时间范围、套件、环境、触发方式、创建人

### 14.10 运行详情（实时）/runs/:runId

布局

- 顶部摘要：状态、进度（完成用例数/总数）、耗时、触发信息、Worker 数
- 左侧用例树（Suite Items）：支持按状态过滤（fail only）
- 右侧详情面板（选中某 case_run 显示）
  - 基本：状态、耗时、重试次数
  - 日志：流式输出（SSE/WebSocket），支持关键字搜索，日志分级（INFO/WARN/ERROR）
  - 产物：请求/响应（脱敏）
  - AI 归因（V1.2）：分类 + 建议
  - 操作：创建缺陷（带预填字段）、复制复现信息
    状态刷新
- running：SSE 推送（推荐），失败回退轮询 2s
- completed：静态展示，支持“生成 AI 分析”（V1.2）

### 14.11 报告中心 /reports

Tab1 单次报告

- 与 Run 详情可复用报告视图（支持导出 PDF 可选）
  Tab2 趋势看板
- 时间范围：7/14/30 天
- 指标：通过率、失败数、不稳定率（flake）、平均耗时
- 维度：按套件/标签/类型/维护人

### 14.12 环境管理 /settings/environments

列表列

- 环境名、baseUrl、健康状态、最近探测时间、操作（编辑/复制/删除）
  编辑抽屉
- name
- baseUrl
- variables（kv 表格）
- secrets（仅展示 key，不回显 value；支持覆盖更新）
- healthCheck 配置：url、timeout、expectedStatus

## 15. 后端接口契约（可直接开工的请求/响应示例）

统一响应：

text

复制下载

```
{ "code": 0, "message": "ok", "data": {}, "requestId": "req_..." }
```



### 15.1 认证

POST /api/auth/login

text

复制下载

```
{ "username": "qa@example.com", "password": "******" }
```



返回：

text

复制下载

```
{ "code": 0, "message": "ok", "data": { "accessToken": "jwt", "expiresIn": 7200 } }
```



GET /api/auth/me

text

复制下载

```
{ "code": 0, "data": { "userId": "u1", "email": "qa@example.com", "name": "QA", "roles": ["Editor"], "tenantId": "t1" } }
```



### 15.2 项目

POST /api/projects

text

复制下载

```
{ "name": "支付项目", "description": "支付域回归", "ownerId": "u1" }
```



GET /api/projects?page=1&pageSize=20&keyword=支付

text

复制下载

```
{ "code": 0, "data": { "page": 1, "pageSize": 20, "total": 1, "items": [ { "id": "p1", "name": "支付项目", "ownerId": "u1", "memberCount": 12, "createdAt": 1710000000 } ] } }
```



### 15.3 环境

POST /api/projects/{projectId}/environments

text

复制下载

```
{
  "name": "staging",
  "baseUrl": "https://stg.example.com",
  "variables": { "tenantId": "1001" },
  "secrets": { "dbPassword": "******" },
  "healthCheck": { "url": "/health", "timeoutMs": 1500, "expectedStatus": 200 }
}
```



说明： secrets 后端加密存储且不回显，仅支持覆盖更新。

### 15.4 用例

POST /api/testcases

text

复制下载

```
{
  "projectId": "p1",
  "title": "创建订单-正常流程",
  "type": "API",
  "priority": "P0",
  "status": "DRAFT",
  "tags": ["order", "smoke"],
  "contentMd": "## 前置条件...\n## 步骤...\n## 期望..."
}
```



GET /api/testcases?projectId=p1&type=API&status=REVIEWED&tag=smoke&page=1&pageSize=20

GET /api/testcases/{id} 返回 data 示例：

text

复制下载

```
{
  "id": "tc1",
  "projectId": "p1",
  "title": "创建订单-正常流程",
  "type": "API",
  "priority": "P0",
  "status": "DRAFT",
  "tags": ["order"],
  "ownerId": "u1",
  "version": 3,
  "contentMd": "..."
}
```



PUT /api/testcases/{id}

- 采用乐观锁：请求头 If-Match: version 或 body 里带 version

### 15.5 套件

POST /api/suites

text

复制下载

```
{ "projectId": "p1", "name": "支付冒烟", "defaultEnvId": "env1", "config": { "timeoutSec": 600, "concurrency": 4, "retryCount": 1, "failFast": false, "variables": {} } }
```



POST /api/suites/{suiteId}/items

text

复制下载

```
{ "items": [ { "testcaseId": "tc1", "orderNo": 1, "params": { "user": "A" } }, { "testcaseId": "tc2", "orderNo": 2, "params": {} } ] }
```



### 15.6 Run（执行）

POST /api/runs

text

复制下载

```
{
  "projectId": "p1",
  "suiteId": "s1",
  "envId": "env1",
  "triggerType": "MANUAL",
  "meta": { "gitCommit": "abc", "pipelineId": "123" },
  "notifyRuleId": "nr1"
}
```



GET /api/runs/{runId}

text

复制下载

```
{
  "code": 0,
  "data": {
    "id": "r1",
    "status": "RUNNING",
    "progress": { "done": 12, "total": 80 },
    "suiteId": "s1",
    "envId": "env1",
    "startAt": 1710000000
  }
}
```



GET /api/runs/{runId}/case-runs?status=FAILED&page=1&pageSize=50

POST /api/runs/{runId}/cancel

- 仅 queued/running 可取消，取消后进入 CANCELED

**POST /api/runs/debug**（调试模式）

text

复制下载

```
{
  "projectId": "p1",
  "testcaseId": "tc1",
  "envId": "env1",
  "params": { "user": "A" }
}
```



返回：直接返回 case_run 结果，同上报格式。

### 15.7 产物

GET /api/artifacts/{artifactId} 返回：

text

复制下载

```
{ "code": 0, "data": { "id": "a1", "type": "API_EXCHANGE", "signedUrl": "https://...&expires=...", "meta": { "name": "exchange.json" } } }
```



### 15.8 AI（V1.1）

POST /api/ai/generate-testcases

text

复制下载

```
{
  "projectId": "p1",
  "input": {
    "apiCollectionId": "ac1",
    "apiRequestId": "req1"  // 可选，若为空则基于整个集合生成
  },
  "options": { "count": 5, "includeBoundary": true, "includeAbnormal": true }
}
```



返回：生成草稿列表（不直接入库）

text

复制下载

```
{ "code": 0, "data": { "recordId": "ai1", "drafts": [ { "title": "...", "contentMd": "...", "tags": ["..."], "priority": "P1" } ] } }
```



POST /api/ai/analyze-run/{runId}

- 异步：返回 taskId，前端轮询 /api/ai/tasks/{taskId} 或 SSE 推送完成事件

### 15.9 Worker 协议（V1 关键，能直接开发 Worker）

POST /api/workers/register

text

复制下载

```
{ "name": "worker-01", "capabilities": ["API"], "slots": 4, "version": "1.0.0" }
```



返回：

text

复制下载

```
{ "code": 0, "data": { "workerId": "w1", "token": "wk_xxx" } }
```



鉴权：后续 worker 请求 header Authorization: Bearer wk_xxx

POST /api/workers/heartbeat

text

复制下载

```
{ "workerId": "w1", "slotsFree": 2, "runningJobIds": ["j1"], "meta": { "cpu": 0.7, "mem": 0.6 } }
```



POST /api/workers/poll

text

复制下载

```
{ "workerId": "w1", "capabilities": ["API"] }
```



返回（无任务）：

text

复制下载

```
{ "code": 0, "data": { "job": null, "sleepMs": 2000 } }
```



返回（有任务）：

text

复制下载

```
{
  "code": 0,
  "data": {
    "job": {
      "jobId": "j1",
      "runId": "r1",
      "env": { "baseUrl": "https://stg.example.com", "variables": { "tenantId": "1001" }, "secrets": { "token": "******" } },
      "suiteConfig": { "timeoutSec": 600, "retryCount": 1, "failFast": false },
      "items": [
        { "caseRunId": "cr1", "testcaseId": "tc1", "type": "API", "contentMd": "...", "params": { "user": "A" } }
      ]
    }
  }
}
```



POST /api/workers/report

text

复制下载

```
{
  "workerId": "w1",
  "jobId": "j1",
  "runId": "r1",
  "results": [
    {
      "caseRunId": "cr1",
      "status": "FAILED",
      "startAt": 1710000000,
      "endAt": 1710000030,
      "errorType": "ASSERT",
      "errorMessage": "statusCode expected 200 but got 500",
      "logs": ["line1", "line2"],
      "artifacts": [
        { "type": "API_EXCHANGE", "storageKey": "runs/r1/cr1/exchange.json", "meta": { "masked": true } }
      ],
      "metrics": { "durationMs": 30000 }
    }
  ],
  "jobStatus": "DONE"
}
```



## 16. 实时日志与事件（前端可直接实现）

推荐 SSE：

- GET /api/runs/{runId}/events （text/event-stream）
  事件类型：
- run_status ：run 状态变更
- case_status ：case_run 状态变更
- log ：某 case_run 日志行，**带日志级别**
- ai_task ：AI 分析任务进度/完成
  事件 payload 示例：

text

复制下载

```
{ "type": "log", "runId": "r1", "caseRunId": "cr1", "ts": 1710000001, "level": "ERROR", "line": "Request POST /order" }
```



## 17. 错误码字典（前后端对齐）

- 0 ：成功
- 40001 ：参数校验失败
- 40101 ：未登录或 token 过期
- 40301 ：无权限
- 40401 ：资源不存在
- 40901 ：版本冲突（乐观锁）
- 42901 ：请求过频
- 50001 ：服务内部错误
- 50301 ：依赖服务不可用（对象存储/队列/模型服务）
  前端文案建议：
- 40901：提示“内容已被他人更新，请刷新后重试”

## 18. 默认配置（产品与实现都可落地）

- Suite 默认：
  - timeoutSec=600
  - concurrency=4
  - retryCount=1
  - retryOnlyOn=["NETWORK","TIMEOUT","FLAKE"]
  - failFast=false
- Run 状态机：
  - QUEUED -> RUNNING -> (PASSED|FAILED|CANCELED)
- CaseRun 状态：
  - QUEUED|RUNNING|PASSED|FAILED|SKIPPED
- 产物类型：
  - API_EXCHANGE|SCREENSHOT|VIDEO|TRACE|LOG_BUNDLE|PERF_REPORT
- **日志级别：INFO, WARN, ERROR**

## 19. 权限矩阵（可直接实现 RBAC）

- Viewer：查看项目、资产、run、报告；不可新建/编辑/删除；**可单独授权“触发执行”**
- Editor：Viewer + 新建/编辑资产、创建 run、重跑、生成 AI 草稿、创建缺陷
- Owner：Editor + 管理项目成员、环境、通知规则、集成（项目级）
- Admin：全局 tenant、用户、系统级集成、审计查看

## 20. 需求拆分（用户故事/开发任务口径，研发可直接排期）

### Epic A：基础与权限

- A1 登录鉴权（JWT），获取当前用户
- A2 租户/项目/成员与 RBAC（含数据隔离）
- A3 审计日志（增删改/集成变更）

### Epic B：资产中心

- B1 用例 CRUD + 版本管理 + 列表筛选（含字段校验）
- B2 套件 CRUD + 编排（拖拽/顺序/参数）+ 配置
- B3 接口集合（集合/请求/断言模板）+ 导入导出（Postman/Swagger）
- B4 数据集（上传/引用/脱敏展示，仅文件管理）

### Epic C：执行中心

- C1 Run 创建/查询/取消/重跑
- C2 **调试模式**：单用例直接执行
- C3 Worker 注册/心跳/拉取任务/上报结果
- C4 产物索引与签名下载（对象存储对接）
- C5 Run 详情实时事件（SSE）+ 日志与产物查看

### Epic D：报告与质量

- D1 单次报告（聚合 case_runs + 失败详情）
- D2 趋势看板（7/14/30 天聚合，通过率、失败数、不稳定率）
- D3 质量门禁（仅展示，V1.1）

### Epic E：AI 能力（V1.1）

- E1 AI 用例生成（基于接口定义，草稿输出 + 采纳入库）
- E2 AI 失败归因（V1.2：错误聚类+人工标签）

### Epic F：集成

- F1 通知（Webhook 自定义，支持飞书/企微/邮件）
- F2 缺陷系统对接（Jira/禅道任选其一），支持多实例配置

## 21. 验收用例（平台自身的测试点）

- 用例/套件：并发编辑触发 409 冲突；筛选/分页正确；版本回溯可用；**字段校验生效**
- 执行：同一 run 取消后 worker 上报结果应被拒收或标记为 canceled；**调试模式返回正确结果**
- 产物：签名 URL 过期不可访问；无权限用户不可下载
- Worker：断连后 job 回收并重新分配；重复上报幂等（按 jobId+caseRunId）
- AI：生成记录可追溯（prompt、模型、输出、采纳人）；采纳后生成 testcase 并关联 recordId
- 集成：通知失败可重试并记录；创建缺陷成功回链到报告页
- **安全：跨租户数据无法访问**

## 22. 开发约束与风险（开工前对齐）

- 密钥与响应内容脱敏：API_EXCHANGE 默认脱敏存储（token/密码/手机号等规则）
- 存储策略：DB 存元数据，对象存储存大文件；提供清理策略（保留期/按项目）
- Worker 执行器选型：V1 先落地 API 执行器，UI 执行器用 Playwright 独立容器运行（V1.1），插件化接口预留。
- AI 模型与成本：V1.1 先做“基于接口定义的用例生成”，使用规则模板+少量模型微调，避免高成本。
- **多租户数据隔离：所有表必须带 tenant_id，API 层自动注入，确保跨租户数据不可见。**
- **脱敏规则：需与业务方确认敏感字段列表，并在存储和展示时统一处理。**

## 23. 开工清单（团队立刻能动起来）

- 设计稿：按第 14 节页面规格出 Figma（或 AntD Pro 原型）
- 后端：按第 15 节接口契约建 OpenAPI/Swagger（先 mock）
- 数据库：按第 8 节表结构建迁移脚本 + 索引
- Worker：按第 15.9 节协议实现最小可用 worker（先支持 API 用例执行）
- 联调：先跑通闭环——创建套件 → 触发 run → worker 执行 → 上报 → 报告展示