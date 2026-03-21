# 后端接口文档（FastAPI）

## 1. 概述

- **框架：** FastAPI
- **统一前缀：** `/api`
- **健康检查：** `/health`
- **统一响应包装：** `ApiResponse<T>`
  - `code`: int（0 表示成功；非 0 表示业务/校验/鉴权等错误）
  - `message`: string（默认 `ok`，错误时为错误描述）
  - `data`: T | null
  - `requestId`: string（用于链路追踪）
- **注意：** 本项目的全局异常处理会把很多错误以 **HTTP 200** 返回（`code` 非 0），请以 `code` 判断成功与否。

## 2. 鉴权

### 2.1 用户鉴权（业务接口）

除 `health`、`/api/auth/register`、`/api/auth/login` 外，多数接口需要登录态。

支持两种方式（任一即可）：

1) `Authorization: Bearer <accessToken>`

2) 透传头（用于网关/内部调用）：
- `X-User-Id: <uuid>`
- `X-Tenant-Id: <uuid>`
- `X-Roles: <role1,role2,...>`（可选）

### 2.2 Worker 鉴权（Worker 接口）

`/api/workers/heartbeat`、`/api/workers/poll`、`/api/workers/report` 依赖 worker 鉴权（由后端校验 worker token，具体见服务实现）。

## 3. 约定

### 3.1 常用请求头

- `X-Request-Id`（可选）：链路追踪 ID；不传则服务端生成 `req_xxxxxxxxxxxxxxxx`
- `Idempotency-Key`（可选）：幂等键（部分接口支持，最大 128 字符）

### 3.2 枚举值

- `TestCaseType`: `API` | `UI` | `PERF` | `MIX`
- `Priority`: `P0` | `P1` | `P2` | `P3`
- `TestCaseStatus`: `DRAFT` | `REVIEWED` | `DEPRECATED`
- `TriggerType`: `MANUAL` | `CRON` | `CI` | `WEBHOOK`
- `RunStatus`: `QUEUED` | `RUNNING` | `PASSED` | `FAILED` | `CANCELED`
- `CaseRunStatus`: `QUEUED` | `RUNNING` | `PASSED` | `FAILED` | `SKIPPED`
- `ArtifactType`: `API_EXCHANGE` | `SCREENSHOT` | `VIDEO` | `TRACE` | `LOG_BUNDLE` | `PERF_REPORT`
- `AiImportSourceType`: `PRD_DOC` | `FIGMA_LINK` | `HTML_DOC`
- `AiImportJobStatus`: `PENDING` | `UPLOADED` | `RUNNING` | `SUCCEEDED` | `FAILED` | `COMMITTED`
- `JobStatus`: `QUEUED` | `RUNNING` | `DONE` | `FAILED` | `CANCELED`

### 3.3 错误码（`code`）映射

全局异常处理会将 HTTP 状态映射为业务码（并以 HTTP 200 返回）：

| 场景 | HTTP 状态 | code |
|------|----------:|-----:|
| 参数校验失败 | 400 / 422 | 40001 |
| 未登录/无权限 | 401 | 40101 |
| 禁止访问 | 403 | 40301 |
| 资源不存在 | 404 | 40401 |
| 方法不允许 | 405 | 40501 |
| 冲突 | 409 | 40901 |
| 限流 | 429 | 42901 |
| DB 不可用 | 503 | 50301 |
| 未知异常 | 500 | 50001 |

## 4. 健康检查

### 4.1 健康检查

**请求 URL：** `GET /health`

**鉴权：** 无

**请求参数：** 无

**响应示例：**
```json
{
  "status": "ok"
}
```

## 5. 认证（Auth）

### 5.1 注册

**请求 URL：** `POST /api/auth/register`

**鉴权：** 无

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|------|------|------|------|------|
| phone | string | 是 | 手机号 | `^1[3-9]\\d{9}$`，11-20 |
| username | string | 是 | 用户名 | 3-64 |
| password | string | 是 | 密码 | 8-128，需包含字母和数字 |
| confirmPassword | string | 是 | 确认密码 | 8-128，需与 password 相同 |
| captcha | string | 是 | 验证码 | 1-16 |

**请求示例：**
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "13800000000",
    "username": "demo",
    "password": "demo12345",
    "confirmPassword": "demo12345",
    "captcha": "1234"
  }'
```

**响应 data：**
| 字段 | 类型 | 说明 |
|------|------|------|
| userId | string | 用户 ID |
| phone | string | 手机号 |
| username | string | 用户名 |
| createdAt | int | Unix 秒级时间戳 |

### 5.2 登录

**请求 URL：** `POST /api/auth/login`

**鉴权：** 无

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名/邮箱（字段名为 username） |
| password | string | 是 | 密码 |

**响应 data：**
| 字段 | 类型 | 说明 |
|------|------|------|
| accessToken | string | JWT |
| expiresIn | int | 过期秒数 |

### 5.3 登出

**请求 URL：** `POST /api/auth/logout`

**鉴权：** 需要

**请求体：** 无

**响应 data：**
| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 默认 true |

### 5.4 当前用户信息

**请求 URL：** `GET /api/auth/me`

**鉴权：** 需要

**响应 data：**
| 字段 | 类型 | 说明 |
|------|------|------|
| userId | string | 用户 ID |
| email | string \| null | 邮箱 |
| phone | string \| null | 手机号 |
| username | string \| null | 用户名 |
| name | string | 显示名 |
| roles | string[] | 角色列表 |
| tenantId | string | 租户 ID |

## 6. 项目（Projects）

### 6.1 创建项目

**请求 URL：** `POST /api/projects`

**鉴权：** 需要

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|------|------|------|------|------|
| name | string | 是 | 项目名 | 1-255 |
| description | string \| null | 否 | 描述 | <= 2000 |
| ownerId | string | 是 | 拥有者用户 ID | uuid 字符串 |

**响应 data：** ProjectDetailData

### 6.2 项目列表/搜索

**请求 URL：** `GET /api/projects`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 页大小，默认 20 |
| keyword | string \| null | 否 | 关键词 |
| key | string \| null | 否 | keyword 的别名（当 keyword 缺省时生效） |
| id | string \| null | 否 | 指定项目 ID（存在时返回单条） |

**响应 data：** PageData\<ProjectListItem\>

### 6.3 首页统计

**请求 URL：** `GET /api/projects/home-stats`

**鉴权：** 需要

**响应 data：**
| 字段 | 类型 | 说明 |
|------|------|------|
| projectTotal | int | 项目数 |
| testcaseTotal | int | 用例数 |
| todayRunTotal | int | 今日执行数 |
| todayPassRate | number | 今日通过率（0-100） |

### 6.4 项目详情

**请求 URL：** `GET /api/projects/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | uuid | 是 | 项目 ID |

### 6.5 更新项目

**请求 URL：** `PUT /api/projects/{id}` 或 `PUT /api/projects?id={id}`

**鉴权：** 需要

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string \| null | 否 | 项目名 |
| description | string \| null | 否 | 描述 |
| ownerId | string \| null | 否 | 拥有者用户 ID |

### 6.6 删除项目

**请求 URL：** `DELETE /api/projects/{id}` 或 `DELETE /api/projects?id={id}`

**鉴权：** 需要

## 7. API 目标（Api Targets）

### 7.1 列表

**请求 URL：** `GET /api/api-targets`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目 ID（uuid 字符串） |
| page | int | 否 | 默认 1，>=1 |
| pageSize | int | 否 | 默认 20，1-200 |

**响应 data：** PageData\<ApiTargetListItem\>

### 7.2 创建

**请求 URL：** `POST /api/api-targets`

**鉴权：** 需要

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目 ID |
| name | string | 是 | 名称 |
| baseUrl | string | 是 | Base URL |
| defaultMethod | string \| null | 否 | 默认方法 |
| defaultPath | string \| null | 否 | 默认路径 |
| headers | object | 否 | 默认 headers |
| authRef | object | 否 | 认证引用 |
| timeoutMs | int | 否 | 默认 10000，1-600000 |
| enabled | boolean | 否 | 默认 true |

**响应 data：** ApiTargetDetail

### 7.3 更新

**请求 URL：** `PUT /api/api-targets/{id}`

**鉴权：** 需要

**路径参数：** `id`（uuid）

**请求体（JSON）：** ApiTargetUpdateRequest（包含 version）

### 7.4 删除

**请求 URL：** `DELETE /api/api-targets/{id}`

**鉴权：** 需要

## 8. 测试用例（Testcases）

### 8.1 创建 AI 导入任务

**请求 URL：** `POST /api/testcases/ai-import/jobs`

**鉴权：** 需要

**请求头：**
| Header | 必填 | 说明 |
|--------|------|------|
| Idempotency-Key | 否 | 幂等键，<=128 |

**请求体（JSON）：** AiImportCreateJobRequest
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目 ID |
| sourceType | AiImportSourceType | 是 | 来源类型 |
| source | object | 否 | 来源引用（figmaUrl/prdUrl/htmlUrl/fileName） |
| generateConfig | object | 否 | 生成参数 |
| skillConfig | object | 否 | 技能开关 |

**响应 data：** AiImportCreateJobData

### 8.2 上传 AI 导入文件（multipart）

**请求 URL：** `POST /api/testcases/ai-import/jobs/{jobId}/file`

**鉴权：** 需要

**路径参数：** `jobId`（uuid）

**请求体：** `multipart/form-data`
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 上传文件 |
| filename | string | 是 | 文件名 |
| sourceType | AiImportSourceType | 是 | 来源类型 |

**响应 data：** AiImportUploadJobFileData

### 8.3 获取 AI 导入任务

**请求 URL：** `GET /api/testcases/ai-import/jobs/{jobId}`

**鉴权：** 需要

**响应 data：** AiImportGetJobData（包含 previewItems）

### 8.4 创建测试用例

**请求 URL：** `POST /api/testcases`

**鉴权：** 需要

**请求体（JSON）：** TestCaseCreateRequest
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目 ID |
| title | string | 是 | 标题 |
| type | TestCaseType | 是 | 用例类型 |
| priority | Priority | 是 | 优先级 |
| status | TestCaseStatus | 是 | 状态 |
| tags | string[] | 否 | 标签（最多 50） |
| contentMd | string | 否 | Markdown 内容 |
| ownerId | string \| null | 否 | 负责人 |
| feature | string | 是 | Feature |
| apiMethod | string | 是 | API 方法 |
| apiUrl | string | 是 | API URL |
| apiParams | object | 否 | 参数 |
| apiHeaders | object | 否 | Header |
| expectedResult | string | 是 | 期望结果 |

**响应 data：** TestCaseDetail

### 8.5 测试用例列表

**请求 URL：** `GET /api/testcases`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目 ID |
| title | string \| null | 否 | 标题（1-100） |
| type | TestCaseType \| null | 否 | 类型 |
| status | TestCaseStatus \| null | 否 | 状态 |
| tag | string \| null | 否 | 标签 |
| ownerId | string \| null | 否 | 负责人 |
| page | int | 否 | 默认 1 |
| pageSize | int | 否 | 默认 20 |

**响应 data：** PageData\<TestCaseListItem\>

### 8.6 负责人选项

**请求 URL：** `GET /api/testcases/owners`

**鉴权：** 需要

**查询参数：** `projectId`（必填）

**响应 data：** TestCaseOwnerOption[]

### 8.7 测试用例详情

**请求 URL：** `GET /api/testcases/{id}`

**鉴权：** 需要

### 8.8 更新测试用例

**请求 URL：** `PUT /api/testcases/{id}`

**鉴权：** 需要

**请求体（JSON）：** TestCasePutRequest（全量字段）

### 8.9 删除测试用例

**请求 URL：** `DELETE /api/testcases/{id}`

**鉴权：** 需要

### 8.10 测试用例版本列表

**请求 URL：** `GET /api/testcases/{id}/versions`

**鉴权：** 需要

**响应 data：** TestCaseVersionSchema[]

### 8.11 恢复到指定版本

**请求 URL：** `POST /api/testcases/{id}/restore`

**鉴权：** 需要

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| version | string | 是 | 版本号（形如 v1.3） |

## 9. 用例绑定（Testcase Bindings）

### 9.1 绑定列表（按用例）

**请求 URL：** `GET /api/testcases/{testcaseId}/bindings`

**鉴权：** 需要

**路径参数：** `testcaseId`（uuid）

**查询参数：** `page`（默认 1），`pageSize`（默认 20）

### 9.2 创建绑定（按用例）

**请求 URL：** `POST /api/testcases/{testcaseId}/bindings`

**鉴权：** 需要

**请求体（JSON）：** TestcaseBindingCreateRequest

### 9.3 更新绑定

**请求 URL：** `PUT /api/testcase-bindings/{bindingId}`

**鉴权：** 需要

**请求体（JSON）：** TestcaseBindingUpdateRequest（包含 version）

### 9.4 删除绑定

**请求 URL：** `DELETE /api/testcase-bindings/{bindingId}`

**鉴权：** 需要

## 10. 套件（Suites）

### 10.1 创建套件

**请求 URL：** `POST /api/suites`

**鉴权：** 需要

**请求体（JSON）：** SuiteCreateRequest

### 10.2 套件列表

**请求 URL：** `GET /api/suites`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string \| null | 否 | 项目过滤 |
| page | int | 否 | 默认 1 |
| pageSize | int | 否 | 默认 20 |

### 10.3 套件详情

**请求 URL：** `GET /api/suites/{id}`

### 10.4 更新套件

**请求 URL：** `PUT /api/suites/{id}`

**请求体（JSON）：** SuitePutRequest

### 10.5 删除套件

**请求 URL：** `DELETE /api/suites/{id}`

### 10.6 批量写入套件用例项（Upsert）

**请求 URL：** `POST /api/suites/{suiteId}/items`

**请求体（JSON）：** SuiteItemsUpsertRequest（items 最多 10000）

### 10.7 获取套件用例项

**请求 URL：** `GET /api/suites/{suiteId}/items`

## 11. 环境（Environments）

### 11.1 创建环境

**请求 URL：** `POST /api/projects/{projectId}/environments`

**鉴权：** 需要

**请求体（JSON）：** EnvironmentCreateRequest

### 11.2 环境列表

**请求 URL：** `GET /api/projects/{projectId}/environments`

**鉴权：** 需要

### 11.3 环境详情

**请求 URL：** `GET /api/projects/{projectId}/environments/{envId}`

### 11.4 更新环境

**请求 URL：** `PUT /api/projects/{projectId}/environments/{envId}`

**请求体（JSON）：** EnvironmentUpdateRequest（仅更新传入字段）

### 11.5 删除环境

**请求 URL：** `DELETE /api/projects/{projectId}/environments/{envId}`

## 12. 执行（Runs）

### 12.1 创建执行（按套件）

**请求 URL：** `POST /api/runs`

**鉴权：** 需要

**请求头：** `Idempotency-Key`（可选，<=128）

**请求体（JSON）：** RunCreateRequest

### 12.2 执行列表

**请求 URL：** `GET /api/runs`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string \| null | 否 | 项目过滤 |
| status | RunStatus \| null | 否 | 状态过滤 |
| from | int \| null | 否 | 起始时间（Unix 秒，参数名为 from） |
| to | int \| null | 否 | 结束时间（Unix 秒，参数名为 to） |
| page | int | 否 | 默认 1 |
| pageSize | int | 否 | 默认 20 |

### 12.3 创建执行（按用例绑定列表）

**请求 URL：** `POST /api/runs/from-testcases`

**鉴权：** 需要

**请求体（JSON）：** RunFromTestcasesRequest（items 至多 10000）

### 12.4 创建执行（按 HTTP 用例列表）

**请求 URL：** `POST /api/runs/from-testcases-http`

**鉴权：** 需要

**请求体（JSON）：** RunFromTestcasesHttpRequest

### 12.5 执行详情

**请求 URL：** `GET /api/runs/{runId}`

### 12.6 生成 Allure 报告

**请求 URL：** `POST /api/runs/{runId}/allure-report/generate`

**鉴权：** 需要

**响应 data：** RunAllureReportGenerateData（成功时返回 reportUrl）

### 12.7 获取 Allure 报告（静态文件）

**请求 URL：**
- `GET /api/runs/{runId}/allure-report/`
- `GET /api/runs/{runId}/allure-report/{asset_path}`

**鉴权：**
- 支持 `access_token` 查询参数（或 Referer query 中的 access_token）
- 或 `Authorization: Bearer ...`
- 或 `X-User-Id` + `X-Tenant-Id`（可选 `X-Roles`）

### 12.8 用例执行列表（Case Runs）

**请求 URL：** `GET /api/runs/{runId}/case-runs`

**查询参数：** `status`（可选），`page`（默认 1），`pageSize`（默认 50）

**响应 data：** PageData\<CaseRunListItem\>

### 12.9 取消执行

**请求 URL：** `POST /api/runs/{runId}/cancel`

### 12.10 重试执行

**请求 URL：** `POST /api/runs/{runId}/retry`

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| failedOnly | boolean | 否 | 默认 true，仅重试失败项 |

## 13. API 集合（Collections）

### 13.1 集合列表

**请求 URL：** `GET /api/collections`

**查询参数：** `projectId`（必填），`page`（默认 1），`pageSize`（默认 20）

**响应 data：** PageData\<CollectionListItem\>

### 13.2 创建集合

**请求 URL：** `POST /api/collections`

**请求体（JSON）：** CollectionCreateRequest

### 13.3 集合详情（含分组与请求）

**请求 URL：** `GET /api/collections/{collectionId}`

**响应 data：** ApiCollectionDetail

### 13.4 更新集合

**请求 URL：** `PUT /api/collections/{collectionId}`

**请求体（JSON）：** CollectionUpdateRequest（仅更新传入字段；variables 可显式置空/覆盖）

### 13.5 删除集合

**请求 URL：** `DELETE /api/collections/{collectionId}`

### 13.6 创建分组

**请求 URL：** `POST /api/collections/{collectionId}/groups`

**请求体（JSON）：** GroupCreateRequest

### 13.7 更新/重排分组

**请求 URL：** `PUT /api/collections/{collectionId}/groups`

**请求体（JSON）：**
- `GroupsReorderRequest`（`groups` 字段为 `[{id, order}]`）
- 或 `GroupUpdateByIdRequest`（`groupId` + `name`）

### 13.8 更新分组（按 ID）

**请求 URL：** `PUT /api/collections/{collectionId}/groups/{groupId}`

**请求体（JSON）：** GroupUpdateRequest

### 13.9 删除分组

**请求 URL：** `DELETE /api/collections/{collectionId}/groups/{groupId}`

### 13.10 创建请求

**请求 URL：** `POST /api/collections/{collectionId}/requests`

**请求体（JSON）：** ApiRequestCreateRequest

### 13.11 获取请求

**请求 URL：** `GET /api/collections/{collectionId}/requests/{requestId}`

### 13.12 更新请求

**请求 URL：** `PUT /api/collections/{collectionId}/requests/{requestId}`

**请求体（JSON）：** ApiRequestCreateRequest

### 13.13 删除请求

**请求 URL：** `DELETE /api/collections/{collectionId}/requests/{requestId}`

### 13.14 导入集合

**请求 URL：** `POST /api/collections/import`

**请求体（JSON）：** ImportCollectionRequest

### 13.15 导出集合

**请求 URL：** `GET /api/collections/{collectionId}/export`

**查询参数：** `format`（必填）

**响应 data：** ExportCollectionData

### 13.16 快速运行集合

**请求 URL：** `POST /api/collections/{collectionId}/run`

**请求体（JSON）：** RunCollectionRequest

### 13.17 快速运行单请求

**请求 URL：** `POST /api/collections/{collectionId}/requests/{requestId}/run`

**请求体（JSON）：** RunApiRequestRequest

## 14. 仪表盘（Dashboard）

路由前缀复用 `/projects`。

### 14.1 Summary

**请求 URL：** `GET /api/projects/{projectId}/dashboard/summary`

**查询参数：** `date`（可选，YYYY-MM-DD）

### 14.2 Failure Top

**请求 URL：** `GET /api/projects/{projectId}/dashboard/failure-top`

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| dimension | string | 否 | 默认 testcase，允许 testcase/suite |
| days | int | 否 | 默认 7，1-90 |
| limit | int | 否 | 默认 10，1-100 |

### 14.3 Trend

**请求 URL：** `GET /api/projects/{projectId}/dashboard/trend`

**查询参数：** `days`（默认 7）

### 14.4 Quality Gate

**请求 URL：** `GET /api/projects/{projectId}/dashboard/quality-gate`

## 15. Worker（Workers）

### 15.1 注册 Worker

**请求 URL：** `POST /api/workers/register`

**鉴权：** 无（但需要 `X-Tenant-Id` 头）

**请求头：**
| Header | 必填 | 说明 |
|--------|------|------|
| X-Tenant-Id | 是 | 租户 ID（uuid） |

**请求体（JSON）：** WorkerRegisterRequest

**响应 data：** WorkerRegisterData（包含 worker token）

### 15.2 心跳

**请求 URL：** `POST /api/workers/heartbeat`

**鉴权：** Worker 鉴权

**请求体（JSON）：** WorkerHeartbeatRequest

### 15.3 拉取任务

**请求 URL：** `POST /api/workers/poll`

**鉴权：** Worker 鉴权

**请求体（JSON）：** WorkerPollRequest

**响应 data：** WorkerPollData（无任务时返回 `job=null` 与 `sleepMs`）

### 15.4 上报任务结果

**请求 URL：** `POST /api/workers/report`

**鉴权：** Worker 鉴权

**请求体（JSON）：** WorkerReportRequest（results 至多 10000）

