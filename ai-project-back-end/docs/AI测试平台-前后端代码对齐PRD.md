# AI 测试平台 PRD（前后端代码对齐版）

文档版本：v1.0  
更新时间：2026-03-19  
文档范围：基于当前仓库 `ai-project_front_end` + `ai-project-back-end` 的已实现代码能力整理，不包含未落地的设想功能。

---

## 1. 产品概述

### 1.1 产品定位

AI 测试平台面向测试工程师、测试开发、研发与管理者，提供“测试资产管理 + 执行编排 + 质量可视化”的统一入口。当前版本以 API 测试管理为核心，已覆盖登录鉴权、项目管理、用例管理、套件管理、仪表盘统计等核心链路。

### 1.2 当前版本目标

1. 支持多项目测试资产管理（项目、用例、套件、环境）。
2. 支持套件编排基础链路（查看套件项）。
3. 支持项目仪表盘质量概览。
4. 打通统一鉴权、统一响应、分页与错误处理约定。

### 1.3 非目标（当前代码未实现）

1. UI 自动化执行编排与结果接入。
2. Worker 管理真实后端联动（当前前端页面为静态展示）。
3. 报告中心真实数据联动（当前前端页面为静态展示）。
4. 测试数据集后端持久化接口联动（当前前端页面为本地交互）。
5. 套件编排“保存”回写接口联动（`POST /api/suites/{suiteId}/items` 前端尚未接入保存动作）。

---

## 2. 目标用户与角色

### 2.1 用户角色

1. 管理员（Admin）：全局管理与跨项目高权限。
2. 项目负责人（Owner）：项目级管理权限。
3. 编辑者（Editor）：可编辑测试资产、配置执行。
4. 查看者（Viewer）：只读查看。

### 2.2 权限原则

1. 接口默认鉴权，除 `/health`、`/api/auth/login`、`/api/auth/register` 外均需身份。
2. 以租户 + 项目维度做权限校验，服务层执行项目读写权限控制。
3. 前端对 40301 等权限错误进行专门提示。

---

## 3. 信息架构与路由

### 3.1 前端主路由

1. 登录注册
   - `/login`
   - `/register`
2. 项目主页
   - `/projects`
3. 项目工作台
   - `/projects/:projectId/dashboard`
   - `/projects/:projectId/assets/testcases`
   - `/projects/:projectId/assets/testcases/:id`
   - `/projects/:projectId/assets/suites`
   - `/projects/:projectId/assets/suites/:id`
   - `/projects/:projectId/assets/apis`
   - `/projects/:projectId/assets/data`
   - `/projects/:projectId/runs`
   - `/projects/:projectId/workers`
   - `/projects/:projectId/reports`
   - `/projects/:projectId/settings/environments`

### 3.2 后端 API 组织

统一前缀：`/api`  
V1 模块：`auth / projects / testcases / suites / environments / runs / collections / dashboard`

---

## 4. 核心业务流程

### 4.1 登录到项目

1. 用户在登录页提交账号密码。
2. 后端返回 `accessToken` 与 `expiresIn`。
3. 前端写入本地存储并在路由守卫校验有效期。
4. 进入 `/projects` 加载用户信息与项目列表。

### 4.2 项目与资产管理

1. 项目列表页加载 `/api/projects` 与 `/api/projects/home-stats`。
2. 进入项目后，侧边栏按 projectId 导航到各资产模块。
3. 用例管理、套件管理分别请求对应后端资源。

### 4.3 套件编排查看流程

1. 套件列表点击“编排”进入 `/projects/:projectId/assets/suites/:id`。
2. 页面请求 `GET /api/suites/{suiteId}/items` 获取套件项。
3. 页面请求 `GET /api/suites/{suiteId}` 获取套件名称。
4. 右侧编排表格展示后端返回用例项。

---

## 5. 功能需求（代码对齐）

## 5.1 认证与账号

### 5.1.1 功能范围

1. 注册
2. 登录
3. 退出登录
4. 获取当前用户信息

### 5.1.2 后端接口

1. `POST /api/auth/register`
2. `POST /api/auth/login`
3. `POST /api/auth/logout`
4. `GET /api/auth/me`

### 5.1.3 前端现状

1. `AuthCard` 已接入注册与登录。
2. `UserProfile` 已接入 `auth/me` 与 `auth/logout`。
3. 鉴权失效会清理 token 并跳回登录页。

---

## 5.2 项目管理

### 5.2.1 功能范围

1. 项目列表查询
2. 项目创建
3. 项目编辑
4. 项目删除
5. 首页聚合统计
6. 项目详情查询（供 Shell 显示项目名）

### 5.2.2 后端接口

1. `GET /api/projects`
2. `POST /api/projects`
3. `GET /api/projects/{id}`
4. `PUT /api/projects/{id}`（兼容 `PUT /api/projects?id=...`）
5. `DELETE /api/projects/{id}`（兼容 `DELETE /api/projects?id=...`）
6. `GET /api/projects/home-stats`

### 5.2.3 关键口径

1. `caseCount`：项目下 testcases 数量。
2. `passRate`：项目下 runs 中 `PASSED/(PASSED+FAILED)*100`，忽略 `RUNNING/QUEUED/CANCELED`。
3. `todayPassRate`：首页当日已完成运行口径通过率。

### 5.2.4 前端现状

1. `/projects` 已接入项目 CRUD 与首页统计。
2. 项目卡片点击进入项目工作台路由。
3. Shell 通过项目详情接口动态展示项目名。

---

## 5.3 仪表盘

### 5.3.1 功能范围

1. 汇总指标
2. 失败 Top
3. 质量门禁
4. 趋势图
5. 最近运行

### 5.3.2 后端接口

1. `GET /api/projects/{projectId}/dashboard/summary`
2. `GET /api/projects/{projectId}/dashboard/failure-top`
3. `GET /api/projects/{projectId}/dashboard/trend`
4. `GET /api/projects/{projectId}/dashboard/quality-gate`
5. 最近运行数据复用 `GET /api/runs`

### 5.3.3 前端现状

1. `Overview.vue` 已接入以上接口并渲染卡片数据。
2. 仪表盘接口由页面内部直接 `fetch` 调用，无独立全局 store。

---

## 5.4 用例管理

### 5.4.1 功能范围

1. 用例列表分页查询
2. 用例筛选（标题/类型/状态）
3. 用例创建
4. 用例详情查看
5. 用例编辑
6. 用例删除
7. 用例版本列表
8. 版本回滚
9. 维护人选项查询

### 5.4.2 后端接口

1. `POST /api/testcases`
2. `GET /api/testcases`
3. `GET /api/testcases/owners`
4. `GET /api/testcases/{id}`
5. `PUT /api/testcases/{id}`（兼容 `PUT /api/testcases?id=...`）
6. `DELETE /api/testcases/{id}`
7. `GET /api/testcases/{id}/versions`
8. `POST /api/testcases/{id}/restore`

### 5.4.3 关键字段与映射

1. 类型：`API/UI/PERF/MIX`
2. 状态：`DRAFT/REVIEWED/DEPRECATED`
3. 优先级：`P0/P1/P2/P3`
4. 前端中文映射已实现（如状态“草稿/已评审/已弃用”）。
5. `lastRun` 与 `updatedAt` 来自后端列表结果直接展示。

### 5.4.4 前端现状

1. `CasesPanel` 已打通主要增删改查链路。
2. 页面会先拉 `auth/me` 与 owners，再拉用例列表。
3. 删除后刷新列表，权限异常有错误提示。

---

## 5.5 测试套件

### 5.5.1 功能范围

1. 套件列表查询
2. 套件创建
3. 套件详情查询
4. 套件更新
5. 套件删除
6. 套件项批量写入
7. 套件项列表查询

### 5.5.2 后端接口

1. `POST /api/suites`
2. `GET /api/suites`
3. `GET /api/suites/{id}`
4. `PUT /api/suites/{id}`
5. `DELETE /api/suites/{id}`
6. `POST /api/suites/{suiteId}/items`
7. `GET /api/suites/{suiteId}/items`

### 5.5.3 前端现状

1. `SuitesPanel` 已接入列表与创建。
2. 套件卡片“编排”已使用真实 `suiteId` 跳转详情页。
3. `SuiteDetailPanel` 已接入 `GET /api/suites/{suiteId}/items` 与 `GET /api/suites/{suiteId}`。
4. 左侧“用例池”当前仍为前端静态数据，未接入 `GET /api/testcases`。
5. “保存”按钮当前仅提示成功，未调用 `POST /api/suites/{suiteId}/items`。

---

## 5.6 环境管理

### 5.6.1 功能范围

1. 环境创建
2. 环境列表
3. 环境详情
4. 环境更新
5. 环境删除

### 5.6.2 后端接口

1. `POST /api/projects/{projectId}/environments`
2. `GET /api/projects/{projectId}/environments`
3. `GET /api/projects/{projectId}/environments/{envId}`
4. `PUT /api/projects/{projectId}/environments/{envId}`
5. `DELETE /api/projects/{projectId}/environments/{envId}`

### 5.6.3 前端现状

1. 套件页与仪表盘页面已消费环境列表做名称映射。
2. 独立“环境管理”页面仍为占位页，未做完整 CRUD UI。

---

## 5.7 运行记录

### 5.7.1 功能范围（后端能力）

1. 创建运行（支持幂等键）
2. 运行列表查询
3. 运行详情查询
4. 子用例运行列表
5. 取消运行
6. 重试运行

### 5.7.2 后端接口

1. `POST /api/runs`
2. `GET /api/runs`
3. `GET /api/runs/{runId}`
4. `GET /api/runs/{runId}/case-runs`
5. `POST /api/runs/{runId}/cancel`
6. `POST /api/runs/{runId}/retry`

### 5.7.3 前端现状

1. 仪表盘“最近运行”已调用 `/api/runs`。
2. `RunsPanel` 主列表当前仍为静态 mock，尚未对接真实运行列表。
3. “新建执行”弹窗在 Shell 内，套件/环境选择当前为本地选项，尚未提交后端 `POST /api/runs`。

---

## 5.8 接口集合（API Collections）

### 5.8.1 功能范围（后端能力）

1. 集合 CRUD
2. 分组 CRUD 与排序
3. 请求 CRUD
4. 导入/导出
5. 集合/单请求快速运行

### 5.8.2 后端接口

1. `GET /api/collections`
2. `POST /api/collections`
3. `GET /api/collections/{collectionId}`
4. `PUT /api/collections/{collectionId}`
5. `DELETE /api/collections/{collectionId}`
6. `POST /api/collections/{collectionId}/groups`
7. `PUT /api/collections/{collectionId}/groups`
8. `PUT /api/collections/{collectionId}/groups/{groupId}`
9. `DELETE /api/collections/{collectionId}/groups/{groupId}`
10. `POST /api/collections/{collectionId}/requests`
11. `GET /api/collections/{collectionId}/requests/{requestId}`
12. `PUT /api/collections/{collectionId}/requests/{requestId}`
13. `DELETE /api/collections/{collectionId}/requests/{requestId}`
14. `POST /api/collections/import`
15. `GET /api/collections/{collectionId}/export`
16. `POST /api/collections/{collectionId}/run`
17. `POST /api/collections/{collectionId}/requests/{requestId}/run`

### 5.8.3 前端现状

1. `ApiCollectionsPanel` 页面结构已搭建。
2. `ApiCollectionsList` 当前为本地静态数据，尚未接入上述后端集合接口。

---

## 5.9 测试数据、报告、Worker、系统设置

### 5.9.1 测试数据

1. 前端 `DataSetsPanel` 为本地文件与列表交互（静态 + 本地内存），未接入后端。
2. 后端当前版本未暴露独立 test-data v1 接口路由。

### 5.9.2 报告中心

1. 前端有 `ReportsPanel` 视图与组件结构。
2. 当前未看到独立 reports 后端 API 对接，属于前端静态展示阶段。

### 5.9.3 Worker 管理

1. 前端 `WorkersPanel` 当前为静态卡片展示。
2. 后端当前版本无 workers v1 路由。

### 5.9.4 设置页

1. 成员权限、集成配置、审计日志路由存在占位页。
2. 仍需后续功能化建设。

---

## 6. 统一技术与接口约定

### 6.1 响应结构

所有业务接口统一：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "requestId": "req_xxx"
}
```

### 6.2 分页结构

```json
{
  "page": 1,
  "pageSize": 20,
  "total": 100,
  "items": []
}
```

### 6.3 鉴权机制

1. 优先 `Authorization: Bearer <token>`。
2. 备选网关透传：`X-User-Id` + `X-Tenant-Id`（可选 `X-Roles`）。

### 6.4 错误处理

1. 后端统一异常映射业务 `code`。
2. 前端普遍以 `response.ok + payload.code===0` 双判定。
3. token 失效时前端统一清理并回登录页。

---

## 7. 数据模型（业务核心）

### 7.1 项目域

1. Project：名称、描述、owner、成员数、创建时间、统计字段（caseCount/passRate）。
2. Environment：name/baseUrl/variables/secrets/healthCheck。

### 7.2 用例域

1. TestCase：title/type/priority/status/tags/owner/version/content。
2. TestCaseVersion：版本快照与回滚。

### 7.3 套件域

1. Suite：name/defaultEnv/config(timeoutSec/concurrency/retryCount)。
2. SuiteItem：suiteId/testcaseId/orderNo/params + testcase展示字段。

### 7.4 执行域

1. Run：project/suite/env/trigger/status/progress/summary。
2. CaseRun：runId + testcaseId + status + 时间 + 错误信息。

### 7.5 接口集合域

1. Collection / Group / Request 分层模型。
2. 支持导入导出与快速运行。

---

## 8. 版本现状评估（前后端对齐）

### 8.1 已完成（可用）

1. 认证登录、用户信息、退出。
2. 项目管理核心链路（列表/创建/编辑/删除/统计）。
3. 仪表盘核心统计接口联动。
4. 用例管理核心 CRUD + 版本。
5. 套件列表与创建。
6. 套件编排详情读取（`GET /api/suites/{suiteId}/items`）。

### 8.2 部分完成（需补全）

1. 套件编排保存未接入（需打通 `POST /api/suites/{suiteId}/items`）。
2. 用例池未接真实用例接口（建议对接 `GET /api/testcases` + 已编排去重）。
3. 运行记录页主列表未接 `/api/runs`。
4. 新建执行弹窗未接 `/api/runs`。
5. 接口集合前端未接 `/api/collections`。

### 8.3 未完成（规划项）

1. 数据集后端能力与前端联动。
2. Worker 管理后端能力与前端联动。
3. 报告中心真实数据接口。
4. 设置页（成员、集成、审计）业务化实现。

---

## 9. 验收标准（按当前目标）

### 9.1 已联调验收项

1. 登录成功后可进入项目主页并拉取用户与项目数据。
2. 项目创建/编辑/删除可成功落库并刷新列表。
3. 用例列表、详情、创建、编辑、删除可闭环。
4. 套件列表/创建可闭环。
5. 套件“编排”可基于真实 suiteId 跳转并读取后端套件项。
6. 仪表盘 summary/failure-top/trend/quality-gate 可正常渲染。

### 9.2 下一阶段验收项

1. 用例池由静态改为 `GET /api/testcases` 实时数据。
2. 编排保存成功后刷新并保持排序一致。
3. 运行记录页改为后端真实分页并支持状态筛选。

---

## 10. 迭代优先级建议

### P0（必须）

1. 套件编排保存接口接入。
2. 用例池接入 `GET /api/testcases`。
3. 运行记录页接入 `/api/runs`。

### P1（高优先）

1. 接口集合前后端联调。
2. 环境管理页面补全 CRUD。
3. 新建执行弹窗接入 `/api/runs` + 幂等键策略。

### P2（中优先）

1. 数据集模块后端能力建设。
2. Worker 管理联调。
3. 报告中心数据化。

---

## 11. 附录：后端路由总表（V1）

1. Auth：4 个接口（register/login/logout/me）
2. Projects：8 个接口（含兼容 put/delete 空路径）
3. Testcases：9 个接口
4. Suites：7 个接口
5. Environments：5 个接口
6. Runs：6 个接口
7. Collections：17 个接口
8. Dashboard：4 个接口

总计：60 个路由处理函数。

