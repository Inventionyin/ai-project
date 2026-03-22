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

`/api/workers/heartbeat`、`/api/workers/poll`、`/api/workers/report` 依赖 worker 鉴权：
- `Authorization: Bearer <workerToken>`

## 3. 约定

### 3.1 常用请求头

- `X-Request-Id`（可选）：链路追踪 ID；不传则服务端生成 `req_xxxxxxxxxxxxxxxx`
- `Idempotency-Key`（可选）：幂等键（部分接口支持，最大 128 字符）

### 3.2 枚举值

- `UserStatus`: ACTIVE | DISABLED
- `ProjectRole`: ADMIN | OWNER | EDITOR | VIEWER
- `TestCaseType`: API | UI | PERF | MIX
- `Priority`: P0 | P1 | P2 | P3
- `TestCaseStatus`: DRAFT | REVIEWED | DEPRECATED
- `TriggerType`: MANUAL | CRON | CI | WEBHOOK
- `RunStatus`: QUEUED | RUNNING | PASSED | FAILED | CANCELED
- `CaseRunStatus`: QUEUED | RUNNING | PASSED | FAILED | SKIPPED
- `ArtifactType`: API_EXCHANGE | SCREENSHOT | VIDEO | TRACE | LOG_BUNDLE | PERF_REPORT
- `AiImportSourceType`: PRD_DOC | FIGMA_LINK | HTML_DOC
- `AiImportJobStatus`: PENDING | UPLOADED | RUNNING | SUCCEEDED | FAILED | COMMITTED
- `JobStatus`: QUEUED | RUNNING | DONE | FAILED | CANCELED
- `WorkerStatus`: ONLINE | OFFLINE

### 3.3 错误码（`code`）映射

全局异常处理会将 HTTP 状态映射为业务码（并以 HTTP 200 返回）：

| 场景 | HTTP 状态 | code |
|--|-------|----|
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

### 4.1 Health

**请求 URL：** `GET /health`

**鉴权：** 无

**请求参数：** 无

**响应：**
```json
{"status":"ok"}
```

## 5. 认证（Auth）

### 5.1 Login

**请求 URL：** `POST /api/auth/login`

**鉴权：** 无

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| username | string | 是 |  | len 1-255 |
| password | string | 是 |  | len 1-128 |

**响应：**
- Schema: `ApiResponse_LoginResponseData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| accessToken | string | 是 |  | len >= 1 |
| expiresIn | integer | 是 |  | >= 1.0 |

### 5.2 Logout

**请求 URL：** `POST /api/auth/logout`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_LogoutResponseData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| success | boolean | 否 |  |  |

### 5.3 Me

**请求 URL：** `GET /api/auth/me`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_MeResponseData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| userId | string | 是 |  | len 1-64 |
| email | string \| null | 否 |  | pattern: ^[^@\s]+@[^@\s]+\.[^@\s]+$；len 3-255 |
| phone | string \| null | 否 |  |  |
| username | string \| null | 否 |  |  |
| name | string | 是 |  | len 1-255 |
| roles | string[] | 是 |  | items >= 0 |
| tenantId | string | 是 |  | len 1-64 |

### 5.4 Register

**请求 URL：** `POST /api/auth/register`

**鉴权：** 无

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| phone | string | 是 |  | pattern: ^1[3-9]\d{9}$；len 11-20 |
| username | string | 是 |  | len 3-64 |
| password | string | 是 |  | len 8-128 |
| confirmPassword | string | 是 |  | len 8-128 |
| captcha | string | 是 |  | len 1-16 |

**响应：**
- Schema: `ApiResponse_RegisterResponseData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| userId | string | 是 |  | len 1-64 |
| phone | string | 是 |  |  |
| username | string | 是 |  |  |
| createdAt | integer | 是 |  | >= 0.0 |

## 6. 项目（Projects）

### 6.1 Delete By Query

**请求 URL：** `DELETE /api/projects`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 6.2 List

**请求 URL：** `GET /api/projects`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 否 |  |  |
| pageSize | integer | 否 |  |  |
| keyword | string \| null | 否 |  |  |
| key | string \| null | 否 |  |  |
| id | string \| null | 否 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_PageData_ProjectListItem__`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 是 |  | >= 1.0 |
| pageSize | integer | 是 |  | 1.0-200.0 |
| total | integer | 是 |  | >= 0.0 |
| items | ProjectListItem[] | 是 |  |  |

### 6.3 Create

**请求 URL：** `POST /api/projects`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string | 是 |  | len 1-255 |
| description | string \| null | 否 |  | len <= 2000 |
| ownerId | string | 是 |  | len 1-64 |

**响应：**
- Schema: `ApiResponse_ProjectDetailData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| description | string \| null | 否 |  | len <= 2000 |
| ownerId | string | 是 |  | len 1-64 |
| memberCount | integer | 是 |  | >= 0.0 |
| createdAt | integer | 是 |  | >= 0.0 |

### 6.4 Update By Query

**请求 URL：** `PUT /api/projects`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string \| null | 否 |  | len 1-255 |
| description | string \| null | 否 |  | len <= 2000 |
| ownerId | string \| null | 否 |  | len 1-64 |

**响应：**
- Schema: `ApiResponse_ProjectDetailData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| description | string \| null | 否 |  | len <= 2000 |
| ownerId | string | 是 |  | len 1-64 |
| memberCount | integer | 是 |  | >= 0.0 |
| createdAt | integer | 是 |  | >= 0.0 |

### 6.5 Home Stats

**请求 URL：** `GET /api/projects/home-stats`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ProjectHomeStatsData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectTotal | integer | 是 |  | >= 0.0 |
| testcaseTotal | integer | 是 |  | >= 0.0 |
| todayRunTotal | integer | 是 |  | >= 0.0 |
| todayPassRate | number | 是 |  | 0.0-100.0 |

### 6.6 Delete

**请求 URL：** `DELETE /api/projects/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 6.7 Get

**请求 URL：** `GET /api/projects/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ProjectDetailData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| description | string \| null | 否 |  | len <= 2000 |
| ownerId | string | 是 |  | len 1-64 |
| memberCount | integer | 是 |  | >= 0.0 |
| createdAt | integer | 是 |  | >= 0.0 |

### 6.8 Update

**请求 URL：** `PUT /api/projects/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string \| null | 否 |  | len 1-255 |
| description | string \| null | 否 |  | len <= 2000 |
| ownerId | string \| null | 否 |  | len 1-64 |

**响应：**
- Schema: `ApiResponse_ProjectDetailData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| description | string \| null | 否 |  | len <= 2000 |
| ownerId | string | 是 |  | len 1-64 |
| memberCount | integer | 是 |  | >= 0.0 |
| createdAt | integer | 是 |  | >= 0.0 |

## 7. API 目标（Api Targets）

### 7.1 List

**请求 URL：** `GET /api/api-targets`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  |  |
| page | integer | 否 |  | >= 1 |
| pageSize | integer | 否 |  | 1-200 |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_PageData_ApiTargetListItem__`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 是 |  | >= 1.0 |
| pageSize | integer | 是 |  | 1.0-200.0 |
| total | integer | 是 |  | >= 0.0 |
| items | ApiTargetListItem[] | 是 |  |  |

### 7.2 Create

**请求 URL：** `POST /api/api-targets`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| baseUrl | string | 是 |  | len 1-2048 |
| defaultMethod | string \| null | 否 |  | len 1-16 |
| defaultPath | string \| null | 否 |  | len <= 1024 |
| headers | Headers | 否 |  |  |
| authRef | Authref | 否 |  |  |
| timeoutMs | integer | 否 |  | 1.0-600000.0 |
| enabled | boolean | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ApiTargetDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| baseUrl | string | 是 |  | len 1-2048 |
| defaultMethod | string \| null | 否 |  | len 1-16 |
| defaultPath | string \| null | 否 |  | len <= 1024 |
| headers | Headers | 否 |  |  |
| authRef | Authref | 否 |  |  |
| timeoutMs | integer | 是 |  | 1.0-600000.0 |
| enabled | boolean | 是 |  |  |
| version | integer | 是 |  | >= 1.0 |
| updatedAt | integer | 是 |  | >= 0.0 |
| createdAt | integer | 是 |  | >= 0.0 |

### 7.3 Delete

**请求 URL：** `DELETE /api/api-targets/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 7.4 Update

**请求 URL：** `PUT /api/api-targets/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string | 是 |  | len 1-255 |
| baseUrl | string | 是 |  | len 1-2048 |
| defaultMethod | string \| null | 否 |  | len 1-16 |
| defaultPath | string \| null | 否 |  | len <= 1024 |
| headers | Headers | 否 |  |  |
| authRef | Authref | 否 |  |  |
| timeoutMs | integer | 是 |  | 1.0-600000.0 |
| enabled | boolean | 是 |  |  |
| version | integer | 是 |  | >= 1.0 |

**响应：**
- Schema: `ApiResponse_ApiTargetDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| baseUrl | string | 是 |  | len 1-2048 |
| defaultMethod | string \| null | 否 |  | len 1-16 |
| defaultPath | string \| null | 否 |  | len <= 1024 |
| headers | Headers | 否 |  |  |
| authRef | Authref | 否 |  |  |
| timeoutMs | integer | 是 |  | 1.0-600000.0 |
| enabled | boolean | 是 |  |  |
| version | integer | 是 |  | >= 1.0 |
| updatedAt | integer | 是 |  | >= 0.0 |
| createdAt | integer | 是 |  | >= 0.0 |

## 8. 用例（Testcases）

### 8.1 List

**请求 URL：** `GET /api/testcases`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  |  |
| title | string \| null | 否 |  | len 1-100 |
| type | TestCaseType \| null | 否 |  |  |
| status | TestCaseStatus \| null | 否 |  |  |
| tag | string \| null | 否 |  |  |
| ownerId | string \| null | 否 |  |  |
| page | integer | 否 |  | >= 1 |
| pageSize | integer | 否 |  | 1-200 |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_PageData_TestCaseListItem__`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 是 |  | >= 1.0 |
| pageSize | integer | 是 |  | 1.0-200.0 |
| total | integer | 是 |  | >= 0.0 |
| items | TestCaseListItem[] | 是 |  |  |

### 8.2 Create

**请求 URL：** `POST /api/testcases`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| testCaseId | string \| null | 否 |  | len 1-64 |
| title | string | 是 |  | len 1-100 |
| type | TestCaseType | 是 |  |  |
| priority | Priority | 是 |  |  |
| status | TestCaseStatus | 是 |  |  |
| tags | string[] | 否 |  | items <= 50 |
| contentMd | string | 否 |  |  |
| ownerId | string \| null | 否 |  | len 1-64 |
| expectedStatusCode | integer \| null | 否 |  | 100.0-599.0 |
| preconditions | string \| null | 否 |  | len 1-5000 |
| postconditions | string \| null | 否 |  | len 1-5000 |
| feature | string | 是 |  | len 1-128 |
| apiMethod | string | 是 |  | len 1-16 |
| apiUrl | string | 是 |  | len 1-1024 |
| apiParams | Apiparams | 否 |  |  |
| apiHeaders | Apiheaders | 否 |  |  |
| expectedResult | string | 是 |  | len 1-5000 |

**响应：**
- Schema: `ApiResponse_TestCaseDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| testCaseId | string \| null | 否 |  | len 1-64 |
| expectedStatusCode | integer \| null | 否 |  | 100.0-599.0 |
| preconditions | string \| null | 否 |  |  |
| postconditions | string \| null | 否 |  |  |
| title | string | 是 |  | len 1-100 |
| type | TestCaseType | 是 |  |  |
| priority | Priority | 是 |  |  |
| status | TestCaseStatus | 是 |  |  |
| tags | string[] | 否 |  | items <= 50 |
| ownerId | string \| null | 否 |  | len 1-64 |
| ownerName | string \| null | 否 |  |  |
| version | string | 是 |  | pattern: ^(?:v?1(?:\.\d+)?)$；len 1-32 |
| contentMd | string | 是 |  |  |
| feature | string \| null | 否 |  | len 1-128 |
| apiMethod | string \| null | 否 |  | len 1-16 |
| apiUrl | string \| null | 否 |  | len 1-1024 |
| apiParams | Apiparams | 否 |  |  |
| apiHeaders | Apiheaders | 否 |  |  |
| expectedResult | string \| null | 否 |  |  |

### 8.3 Create Ai Import Job

**请求 URL：** `POST /api/testcases/ai-import/jobs`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Idempotency-Key | string \| null | 否 |  |  |
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| sourceType | AiImportSourceType | 是 |  |  |
| source | AiImportSourceRef | 否 |  |  |
| generateConfig | AiImportGenerateConfig | 否 |  |  |
| skillConfig | AiImportSkillConfig | 否 |  |  |

**响应：**
- Schema: `ApiResponse_AiImportCreateJobData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| jobId | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| sourceType | AiImportSourceType | 是 |  |  |
| status | AiImportJobStatus | 是 |  |  |
| createdAt | integer | 是 |  | >= 0.0 |

### 8.4 Get Ai Import Job

**请求 URL：** `GET /api/testcases/ai-import/jobs/{jobId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| jobId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_AiImportGetJobData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| jobId | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| sourceType | AiImportSourceType | 是 |  |  |
| status | AiImportJobStatus | 是 |  |  |
| summary | Summary | 否 |  |  |
| previewItems | AiImportPreviewItem[] | 否 |  |  |
| createdAt | integer | 是 |  | >= 0.0 |
| updatedAt | integer | 是 |  | >= 0.0 |

### 8.5 Upload Ai Import Job File

**请求 URL：** `POST /api/testcases/ai-import/jobs/{jobId}/file`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| jobId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_AiImportUploadJobFileData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| jobId | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| sourceType | AiImportSourceType | 是 |  |  |
| status | AiImportJobStatus | 是 |  |  |
| fileName | string | 是 |  | len 1-255 |
| fileSize | integer | 是 |  | >= 1.0 |
| uploadedAt | integer | 是 |  | >= 0.0 |

### 8.6 Owners

**请求 URL：** `GET /api/testcases/owners`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_list_TestCaseOwnerOption__`

### 8.7 Delete

**请求 URL：** `DELETE /api/testcases/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 8.8 Get

**请求 URL：** `GET /api/testcases/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_TestCaseDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| testCaseId | string \| null | 否 |  | len 1-64 |
| expectedStatusCode | integer \| null | 否 |  | 100.0-599.0 |
| preconditions | string \| null | 否 |  |  |
| postconditions | string \| null | 否 |  |  |
| title | string | 是 |  | len 1-100 |
| type | TestCaseType | 是 |  |  |
| priority | Priority | 是 |  |  |
| status | TestCaseStatus | 是 |  |  |
| tags | string[] | 否 |  | items <= 50 |
| ownerId | string \| null | 否 |  | len 1-64 |
| ownerName | string \| null | 否 |  |  |
| version | string | 是 |  | pattern: ^(?:v?1(?:\.\d+)?)$；len 1-32 |
| contentMd | string | 是 |  |  |
| feature | string \| null | 否 |  | len 1-128 |
| apiMethod | string \| null | 否 |  | len 1-16 |
| apiUrl | string \| null | 否 |  | len 1-1024 |
| apiParams | Apiparams | 否 |  |  |
| apiHeaders | Apiheaders | 否 |  |  |
| expectedResult | string \| null | 否 |  |  |

### 8.9 Update

**请求 URL：** `PUT /api/testcases/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| testCaseId | string \| null | 否 |  | len 1-64 |
| title | string | 是 |  | len 1-100 |
| type | TestCaseType | 是 |  |  |
| priority | Priority | 是 |  |  |
| status | TestCaseStatus | 是 |  |  |
| tags | string[] | 否 |  | items <= 50 |
| contentMd | string | 是 |  | len >= 1 |
| ownerId | string \| null | 否 |  | len 1-64 |
| expectedStatusCode | integer \| null | 否 |  | 100.0-599.0 |
| preconditions | string \| null | 否 |  | len 1-5000 |
| postconditions | string \| null | 否 |  | len 1-5000 |
| feature | string | 是 |  | len 1-128 |
| apiMethod | string | 是 |  | len 1-16 |
| apiUrl | string | 是 |  | len 1-1024 |
| apiParams | Apiparams | 否 |  |  |
| apiHeaders | Apiheaders | 否 |  |  |
| expectedResult | string | 是 |  | len 1-5000 |

**响应：**
- Schema: `ApiResponse_TestCaseDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| testCaseId | string \| null | 否 |  | len 1-64 |
| expectedStatusCode | integer \| null | 否 |  | 100.0-599.0 |
| preconditions | string \| null | 否 |  |  |
| postconditions | string \| null | 否 |  |  |
| title | string | 是 |  | len 1-100 |
| type | TestCaseType | 是 |  |  |
| priority | Priority | 是 |  |  |
| status | TestCaseStatus | 是 |  |  |
| tags | string[] | 否 |  | items <= 50 |
| ownerId | string \| null | 否 |  | len 1-64 |
| ownerName | string \| null | 否 |  |  |
| version | string | 是 |  | pattern: ^(?:v?1(?:\.\d+)?)$；len 1-32 |
| contentMd | string | 是 |  |  |
| feature | string \| null | 否 |  | len 1-128 |
| apiMethod | string \| null | 否 |  | len 1-16 |
| apiUrl | string \| null | 否 |  | len 1-1024 |
| apiParams | Apiparams | 否 |  |  |
| apiHeaders | Apiheaders | 否 |  |  |
| expectedResult | string \| null | 否 |  |  |

### 8.10 Restore

**请求 URL：** `POST /api/testcases/{id}/restore`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| version | string | 是 |  | pattern: ^(?:v?1(?:\.\d+)?)$；len 1-32 |

**响应：**
- Schema: `ApiResponse_TestCaseDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| testCaseId | string \| null | 否 |  | len 1-64 |
| expectedStatusCode | integer \| null | 否 |  | 100.0-599.0 |
| preconditions | string \| null | 否 |  |  |
| postconditions | string \| null | 否 |  |  |
| title | string | 是 |  | len 1-100 |
| type | TestCaseType | 是 |  |  |
| priority | Priority | 是 |  |  |
| status | TestCaseStatus | 是 |  |  |
| tags | string[] | 否 |  | items <= 50 |
| ownerId | string \| null | 否 |  | len 1-64 |
| ownerName | string \| null | 否 |  |  |
| version | string | 是 |  | pattern: ^(?:v?1(?:\.\d+)?)$；len 1-32 |
| contentMd | string | 是 |  |  |
| feature | string \| null | 否 |  | len 1-128 |
| apiMethod | string \| null | 否 |  | len 1-16 |
| apiUrl | string \| null | 否 |  | len 1-1024 |
| apiParams | Apiparams | 否 |  |  |
| apiHeaders | Apiheaders | 否 |  |  |
| expectedResult | string \| null | 否 |  |  |

### 8.11 List Versions

**请求 URL：** `GET /api/testcases/{id}/versions`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_list_TestCaseVersionSchema__`

## 9. 用例绑定（Testcase Bindings）

### 9.1 Delete

**请求 URL：** `DELETE /api/testcase-bindings/{bindingId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| bindingId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 9.2 Update

**请求 URL：** `PUT /api/testcase-bindings/{bindingId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| bindingId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string | 是 |  | len 1-255 |
| datasetId | string \| null | 否 |  | len 1-64 |
| apiTargetId | string \| null | 否 |  | len 1-64 |
| params | Params | 否 |  |  |
| priority | integer | 是 |  | 1.0-1000000.0 |
| enabled | boolean | 是 |  |  |
| version | integer | 是 |  | >= 1.0 |

**响应：**
- Schema: `ApiResponse_TestcaseBindingDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| testcaseId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| datasetId | string \| null | 否 |  | len 1-64 |
| apiTargetId | string \| null | 否 |  | len 1-64 |
| params | Params | 否 |  |  |
| priority | integer | 是 |  | 1.0-1000000.0 |
| enabled | boolean | 是 |  |  |
| version | integer | 是 |  | >= 1.0 |
| updatedAt | integer | 是 |  | >= 0.0 |
| createdAt | integer | 是 |  | >= 0.0 |

### 9.3 List

**请求 URL：** `GET /api/testcases/{testcaseId}/bindings`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| testcaseId | string(uuid) | 是 |  |  |

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 否 |  | >= 1 |
| pageSize | integer | 否 |  | 1-200 |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_PageData_TestcaseBindingListItem__`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 是 |  | >= 1.0 |
| pageSize | integer | 是 |  | 1.0-200.0 |
| total | integer | 是 |  | >= 0.0 |
| items | TestcaseBindingListItem[] | 是 |  |  |

### 9.4 Create

**请求 URL：** `POST /api/testcases/{testcaseId}/bindings`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| testcaseId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string | 是 |  | len 1-255 |
| datasetId | string \| null | 否 |  | len 1-64 |
| apiTargetId | string \| null | 否 |  | len 1-64 |
| params | Params | 否 |  |  |
| priority | integer | 否 |  | 1.0-1000000.0 |
| enabled | boolean | 否 |  |  |

**响应：**
- Schema: `ApiResponse_TestcaseBindingDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| testcaseId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| datasetId | string \| null | 否 |  | len 1-64 |
| apiTargetId | string \| null | 否 |  | len 1-64 |
| params | Params | 否 |  |  |
| priority | integer | 是 |  | 1.0-1000000.0 |
| enabled | boolean | 是 |  |  |
| version | integer | 是 |  | >= 1.0 |
| updatedAt | integer | 是 |  | >= 0.0 |
| createdAt | integer | 是 |  | >= 0.0 |

## 10. 套件（Suites）

### 10.1 List

**请求 URL：** `GET /api/suites`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string \| null | 否 |  |  |
| page | integer | 否 |  | >= 1 |
| pageSize | integer | 否 |  | 1-200 |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_PageData_SuitePublic__`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 是 |  | >= 1.0 |
| pageSize | integer | 是 |  | 1.0-200.0 |
| total | integer | 是 |  | >= 0.0 |
| items | SuitePublic[] | 是 |  |  |

### 10.2 Create

**请求 URL：** `POST /api/suites`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| defaultEnvId | string \| null | 否 |  | len 1-64 |
| config | SuiteConfig | 是 |  |  |

**响应：**
- Schema: `ApiResponse_SuitePublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| defaultEnvId | string \| null | 否 |  | len 1-64 |
| config | SuiteConfig | 是 |  |  |
| createdAt | integer | 是 |  | >= 0.0 |
| updatedAt | integer | 是 |  | >= 0.0 |

### 10.3 Delete

**请求 URL：** `DELETE /api/suites/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 10.4 Get

**请求 URL：** `GET /api/suites/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_SuitePublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| defaultEnvId | string \| null | 否 |  | len 1-64 |
| config | SuiteConfig | 是 |  |  |
| createdAt | integer | 是 |  | >= 0.0 |
| updatedAt | integer | 是 |  | >= 0.0 |

### 10.5 Update

**请求 URL：** `PUT /api/suites/{id}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| defaultEnvId | string \| null | 否 |  | len 1-64 |
| config | SuiteConfig | 是 |  |  |

**响应：**
- Schema: `ApiResponse_SuitePublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| defaultEnvId | string \| null | 否 |  | len 1-64 |
| config | SuiteConfig | 是 |  |  |
| createdAt | integer | 是 |  | >= 0.0 |
| updatedAt | integer | 是 |  | >= 0.0 |

### 10.6 List Items

**请求 URL：** `GET /api/suites/{suiteId}/items`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| suiteId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_list_SuiteItemPublic__`

### 10.7 Upsert Items

**请求 URL：** `POST /api/suites/{suiteId}/items`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| suiteId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| items | SuiteItemInput[] | 是 |  | items 1-10000 |

**响应：**
- Schema: `ApiResponse_list_SuiteItemPublic__`

## 11. 环境（Environments）

### 11.1 List

**请求 URL：** `GET /api/projects/{projectId}/environments`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_list_EnvironmentPublic__`

### 11.2 Create

**请求 URL：** `POST /api/projects/{projectId}/environments`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string | 是 |  | len 1-255 |
| baseUrl | string | 是 |  | len 1-2048 |
| variables | Variables | 否 |  |  |
| secrets | Secrets | 否 |  |  |
| healthCheck | HealthCheckConfig \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_EnvironmentPublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| baseUrl | string | 是 |  | len 1-2048 |
| variables | Variables | 否 |  |  |
| secretKeys | string[] | 否 |  |  |
| healthCheck | HealthCheckConfig \| null | 否 |  |  |
| createdAt | integer \| null | 否 |  | >= 0.0 |
| updatedAt | integer \| null | 否 |  | >= 0.0 |

### 11.3 Delete

**请求 URL：** `DELETE /api/projects/{projectId}/environments/{envId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string(uuid) | 是 |  |  |
| envId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 11.4 Get

**请求 URL：** `GET /api/projects/{projectId}/environments/{envId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string(uuid) | 是 |  |  |
| envId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_EnvironmentPublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| baseUrl | string | 是 |  | len 1-2048 |
| variables | Variables | 否 |  |  |
| secretKeys | string[] | 否 |  |  |
| healthCheck | HealthCheckConfig \| null | 否 |  |  |
| createdAt | integer \| null | 否 |  | >= 0.0 |
| updatedAt | integer \| null | 否 |  | >= 0.0 |

### 11.5 Update

**请求 URL：** `PUT /api/projects/{projectId}/environments/{envId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string(uuid) | 是 |  |  |
| envId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string \| null | 否 |  | len 1-255 |
| baseUrl | string \| null | 否 |  | len 1-2048 |
| variables | object \| null | 否 |  |  |
| secrets | object \| null | 否 |  |  |
| healthCheck | HealthCheckConfig \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_EnvironmentPublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| baseUrl | string | 是 |  | len 1-2048 |
| variables | Variables | 否 |  |  |
| secretKeys | string[] | 否 |  |  |
| healthCheck | HealthCheckConfig \| null | 否 |  |  |
| createdAt | integer \| null | 否 |  | >= 0.0 |
| updatedAt | integer \| null | 否 |  | >= 0.0 |

## 12. 执行（Runs）

### 12.1 List

**请求 URL：** `GET /api/runs`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string \| null | 否 |  |  |
| status | RunStatus \| null | 否 |  |  |
| from | integer \| null | 否 |  |  |
| to | integer \| null | 否 |  |  |
| page | integer | 否 |  | >= 1 |
| pageSize | integer | 否 |  | 1-200 |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_PageData_RunDetailData__`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 是 |  | >= 1.0 |
| pageSize | integer | 是 |  | 1.0-200.0 |
| total | integer | 是 |  | >= 0.0 |
| items | RunDetailData[] | 是 |  |  |

### 12.2 Create

**请求 URL：** `POST /api/runs`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Idempotency-Key | string \| null | 否 |  |  |
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| suiteId | string | 是 |  | len 1-64 |
| envId | string | 是 |  | len 1-64 |
| triggerType | TriggerType | 是 |  |  |
| meta | Meta | 否 |  |  |
| notifyRuleId | string \| null | 否 |  | len 1-64 |

**响应：**
- Schema: `ApiResponse_RunDetailData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| status | RunStatus | 是 |  |  |
| progress | RunProgress | 是 |  |  |
| suiteId | string | 是 |  | len 1-64 |
| envId | string \| null | 否 |  | len 1-64 |
| startAt | integer | 是 |  | >= 0.0 |

### 12.3 List Allure Reports

**请求 URL：** `GET /api/runs/allure-reports`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string \| null | 否 |  |  |
| page | integer | 否 |  | >= 1 |
| pageSize | integer | 否 |  | 1-200 |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_PageData_RunAllureReportListItem__`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 是 |  | >= 1.0 |
| pageSize | integer | 是 |  | 1.0-200.0 |
| total | integer | 是 |  | >= 0.0 |
| items | RunAllureReportListItem[] | 是 |  |  |

### 12.4 Create From Testcases

**请求 URL：** `POST /api/runs/from-testcases`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Idempotency-Key | string \| null | 否 |  |  |
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| envId | string | 是 |  | len 1-64 |
| triggerType | TriggerType | 是 |  |  |
| meta | Meta | 否 |  |  |
| concurrency | integer | 否 |  | 1.0-100.0 |
| stopOnFailure | boolean | 否 |  |  |
| items | RunFromTestcasesItem[] | 是 |  | items 1-10000 |
| notifyRuleId | string \| null | 否 |  | len 1-64 |

**响应：**
- Schema: `ApiResponse_RunDetailData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| status | RunStatus | 是 |  |  |
| progress | RunProgress | 是 |  |  |
| suiteId | string | 是 |  | len 1-64 |
| envId | string \| null | 否 |  | len 1-64 |
| startAt | integer | 是 |  | >= 0.0 |

### 12.5 Create From Testcases Http

**请求 URL：** `POST /api/runs/from-testcases-http`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Idempotency-Key | string \| null | 否 |  |  |
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| envId | string \| null | 否 |  | len 1-64 |
| triggerType | TriggerType | 是 |  |  |
| meta | Meta | 否 |  |  |
| concurrency | integer | 否 |  | 1.0-100.0 |
| stopOnFailure | boolean | 否 |  |  |
| items | RunFromTestcasesHttpItem[] | 是 |  | items 1-10000 |
| notifyRuleId | string \| null | 否 |  | len 1-64 |

**响应：**
- Schema: `ApiResponse_RunDetailData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| status | RunStatus | 是 |  |  |
| progress | RunProgress | 是 |  |  |
| suiteId | string | 是 |  | len 1-64 |
| envId | string \| null | 否 |  | len 1-64 |
| startAt | integer | 是 |  | >= 0.0 |

### 12.6 Get

**请求 URL：** `GET /api/runs/{runId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_RunDetailData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| status | RunStatus | 是 |  |  |
| progress | RunProgress | 是 |  |  |
| suiteId | string | 是 |  | len 1-64 |
| envId | string \| null | 否 |  | len 1-64 |
| startAt | integer | 是 |  | >= 0.0 |

### 12.7 Delete Allure Report

**请求 URL：** `DELETE /api/runs/{runId}/allure-report`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_RunAllureReportDeleteData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string | 是 |  | len 1-64 |
| deletedArtifacts | integer | 是 |  | >= 0.0 |
| deletedFiles | integer | 是 |  | >= 0.0 |
| deletedDirs | integer | 是 |  | >= 0.0 |

### 12.8 Delete Allure Report Via Post

**请求 URL：** `POST /api/runs/{runId}/allure-report/delete`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_RunAllureReportDeleteData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string | 是 |  | len 1-64 |
| deletedArtifacts | integer | 是 |  | >= 0.0 |
| deletedFiles | integer | 是 |  | >= 0.0 |
| deletedDirs | integer | 是 |  | >= 0.0 |

### 12.9 Generate Allure Report

**请求 URL：** `POST /api/runs/{runId}/allure-report/generate`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_RunAllureReportGenerateData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string | 是 |  | len 1-64 |
| reportStatus | string | 是 |  |  |
| reportUrl | string \| null | 否 |  |  |
| reportPath | string \| null | 否 |  |  |
| resultsPath | string \| null | 否 |  |  |
| errorCode | string \| null | 否 |  |  |
| errorMessage | string \| null | 否 |  |  |

### 12.10 Cancel

**请求 URL：** `POST /api/runs/{runId}/cancel`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_RunCancelResponseData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string | 是 |  | len 1-64 |
| status | RunStatus | 是 |  |  |

### 12.11 List Case Runs

**请求 URL：** `GET /api/runs/{runId}/case-runs`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string(uuid) | 是 |  |  |

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| status | CaseRunStatus \| null | 否 |  |  |
| page | integer | 否 |  | >= 1 |
| pageSize | integer | 否 |  | 1-200 |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_PageData_CaseRunListItem__`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 是 |  | >= 1.0 |
| pageSize | integer | 是 |  | 1.0-200.0 |
| total | integer | 是 |  | >= 0.0 |
| items | CaseRunListItem[] | 是 |  |  |

### 12.12 Retry

**请求 URL：** `POST /api/runs/{runId}/retry`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| runId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Idempotency-Key | string \| null | 否 |  |  |
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| failedOnly | boolean | 否 |  |  |

**响应：**
- Schema: `ApiResponse_RunDetailData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| status | RunStatus | 是 |  |  |
| progress | RunProgress | 是 |  |  |
| suiteId | string | 是 |  | len 1-64 |
| envId | string \| null | 否 |  | len 1-64 |
| startAt | integer | 是 |  | >= 0.0 |

## 13. API 集合（Collections）

### 13.1 List

**请求 URL：** `GET /api/collections`

**鉴权：** 需要

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  |  |
| page | integer | 否 |  | >= 1 |
| pageSize | integer | 否 |  | 1-200 |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_PageData_CollectionListItem__`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| page | integer | 是 |  | >= 1.0 |
| pageSize | integer | 是 |  | 1.0-200.0 |
| total | integer | 是 |  | >= 0.0 |
| items | CollectionListItem[] | 是 |  |  |

### 13.2 Create

**请求 URL：** `POST /api/collections`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| variables | Variables | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ApiCollectionDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| variables | Variables | 否 |  |  |
| groups | ApiCollectionGroupWithRequests[] | 否 |  |  |
| requests | ApiRequestPublic[] | 否 |  |  |
| updatedAt | integer | 是 |  | >= 0.0 |

### 13.3 Import

**请求 URL：** `POST /api/collections/import`

**鉴权：** 需要

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string | 是 |  | len 1-64 |
| format | string | 是 |  | len 1-32 |
| content | string | 是 |  | len >= 1 |

**响应：**
- Schema: `ApiResponse_ApiCollectionDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| variables | Variables | 否 |  |  |
| groups | ApiCollectionGroupWithRequests[] | 否 |  |  |
| requests | ApiRequestPublic[] | 否 |  |  |
| updatedAt | integer | 是 |  | >= 0.0 |

### 13.4 Delete

**请求 URL：** `DELETE /api/collections/{collectionId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 13.5 Get

**请求 URL：** `GET /api/collections/{collectionId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ApiCollectionDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| variables | Variables | 否 |  |  |
| groups | ApiCollectionGroupWithRequests[] | 否 |  |  |
| requests | ApiRequestPublic[] | 否 |  |  |
| updatedAt | integer | 是 |  | >= 0.0 |

### 13.6 Update

**请求 URL：** `PUT /api/collections/{collectionId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string \| null | 否 |  | len 1-255 |
| variables | object \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ApiCollectionDetail_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| projectId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| variables | Variables | 否 |  |  |
| groups | ApiCollectionGroupWithRequests[] | 否 |  |  |
| requests | ApiRequestPublic[] | 否 |  |  |
| updatedAt | integer | 是 |  | >= 0.0 |

### 13.7 Export

**请求 URL：** `GET /api/collections/{collectionId}/export`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| format | string | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ExportCollectionData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| format | string | 是 |  | len 1-32 |
| content | string | 是 |  | len >= 1 |

### 13.8 Create Group

**请求 URL：** `POST /api/collections/{collectionId}/groups`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string | 是 |  | len 1-255 |

**响应：**
- Schema: `ApiResponse_ApiCollectionGroupPublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| collectionId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| order | integer | 是 |  | >= 0.0 |

### 13.9 Put Groups

**请求 URL：** `PUT /api/collections/{collectionId}/groups`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
- Schema: `GroupsReorderRequest | GroupUpdateByIdRequest`

**响应：**
- Schema: `ApiResponse_list_ApiCollectionGroupPublic__`

### 13.10 Delete Group

**请求 URL：** `DELETE /api/collections/{collectionId}/groups/{groupId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |
| groupId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 13.11 Update Group

**请求 URL：** `PUT /api/collections/{collectionId}/groups/{groupId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |
| groupId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string | 是 |  | len 1-255 |

**响应：**
- Schema: `ApiResponse_ApiCollectionGroupPublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| collectionId | string | 是 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| order | integer | 是 |  | >= 0.0 |

### 13.12 Create Request

**请求 URL：** `POST /api/collections/{collectionId}/requests`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| groupId | string \| null | 否 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| method | string | 是 |  | len 1-16 |
| url | string | 是 |  | len 1-2048 |
| headers | Headers | 否 |  |  |
| auth | Auth | 否 |  |  |
| body | Body | 否 |  |  |
| asserts | Asserts | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ApiRequestPublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| collectionId | string | 是 |  | len 1-64 |
| groupId | string \| null | 否 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| method | string | 是 |  | len 1-16 |
| url | string | 是 |  | len 1-2048 |
| headers | Headers | 否 |  |  |
| auth | Auth | 否 |  |  |
| body | Body | 否 |  |  |
| asserts | Asserts | 否 |  |  |
| updatedAt | integer | 是 |  | >= 0.0 |

### 13.13 Delete Request

**请求 URL：** `DELETE /api/collections/{collectionId}/requests/{requestId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |
| requestId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_dict_`

### 13.14 Get Request

**请求 URL：** `GET /api/collections/{collectionId}/requests/{requestId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |
| requestId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ApiRequestPublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| collectionId | string | 是 |  | len 1-64 |
| groupId | string \| null | 否 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| method | string | 是 |  | len 1-16 |
| url | string | 是 |  | len 1-2048 |
| headers | Headers | 否 |  |  |
| auth | Auth | 否 |  |  |
| body | Body | 否 |  |  |
| asserts | Asserts | 否 |  |  |
| updatedAt | integer | 是 |  | >= 0.0 |

### 13.15 Update Request

**请求 URL：** `PUT /api/collections/{collectionId}/requests/{requestId}`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |
| requestId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| groupId | string \| null | 否 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| method | string | 是 |  | len 1-16 |
| url | string | 是 |  | len 1-2048 |
| headers | Headers | 否 |  |  |
| auth | Auth | 否 |  |  |
| body | Body | 否 |  |  |
| asserts | Asserts | 否 |  |  |

**响应：**
- Schema: `ApiResponse_ApiRequestPublic_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| id | string | 是 |  | len 1-64 |
| collectionId | string | 是 |  | len 1-64 |
| groupId | string \| null | 否 |  | len 1-64 |
| name | string | 是 |  | len 1-255 |
| method | string | 是 |  | len 1-16 |
| url | string | 是 |  | len 1-2048 |
| headers | Headers | 否 |  |  |
| auth | Auth | 否 |  |  |
| body | Body | 否 |  |  |
| asserts | Asserts | 否 |  |  |
| updatedAt | integer | 是 |  | >= 0.0 |

### 13.16 Run Request

**请求 URL：** `POST /api/collections/{collectionId}/requests/{requestId}/run`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |
| requestId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| envId | string \| null | 否 |  | len 1-64 |

**响应：**
- Schema: `ApiResponse_dict_`

### 13.17 Run Collection

**请求 URL：** `POST /api/collections/{collectionId}/run`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| collectionId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| envId | string \| null | 否 |  | len 1-64 |
| concurrency | integer | 否 |  | 1.0-100.0 |
| iterations | integer | 否 |  | 1.0-1000.0 |

**响应：**
- Schema: `ApiResponse_dict_`

## 14. 看板（Dashboard）

### 14.1 Failure Top

**请求 URL：** `GET /api/projects/{projectId}/dashboard/failure-top`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string(uuid) | 是 |  |  |

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| dimension | string \| null | 否 |  |  |
| days | integer | 否 |  | 1-90 |
| limit | integer | 否 |  | 1-100 |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_DashboardFailureTopData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| dimension | string | 是 |  | enum: testcase \| suite |
| items | DashboardFailureTopTestcaseItem \| DashboardFailureTopSuiteItem[] | 否 |  |  |

### 14.2 Quality Gate

**请求 URL：** `GET /api/projects/{projectId}/dashboard/quality-gate`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string(uuid) | 是 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_DashboardQualityGateData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| overall | string | 是 |  | enum: PASSED \| PARTIAL_FAIL \| FAILED \| UNKNOWN |
| lastCheckedAt | integer \| null | 否 |  | >= 0.0 |
| linkedRunId | string \| null | 否 |  | len 1-64 |
| gates | DashboardQualityGateItem[] | 否 |  |  |

### 14.3 Summary

**请求 URL：** `GET /api/projects/{projectId}/dashboard/summary`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string(uuid) | 是 |  |  |

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| date | string(date) \| null | 否 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_DashboardSummaryData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| date | string | 是 |  | len 10-10 |
| totalRuns | integer | 是 |  | >= 0.0 |
| passedRuns | integer | 是 |  | >= 0.0 |
| failedRuns | integer | 是 |  | >= 0.0 |
| runningRuns | integer | 是 |  | >= 0.0 |
| canceledRuns | integer | 是 |  | >= 0.0 |
| passRate | number | 是 |  | >= 0.0 |

### 14.4 Trend

**请求 URL：** `GET /api/projects/{projectId}/dashboard/trend`

**鉴权：** 需要

**路径参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| projectId | string(uuid) | 是 |  |  |

**查询参数：**
| 参数 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| days | integer | 否 |  |  |

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |
| X-User-Id | string \| null | 否 |  |  |
| X-Tenant-Id | string \| null | 否 |  |  |
| X-Roles | string \| null | 否 |  |  |

**响应：**
- Schema: `ApiResponse_DashboardTrendData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| days | integer | 是 |  | enum: 7 \| 14 \| 30 |
| items | DashboardTrendItem[] | 否 |  |  |

## 15. Worker（Workers）

### 15.1 Heartbeat

**请求 URL：** `POST /api/workers/heartbeat`

**鉴权：** 需要（worker token）

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| workerId | string | 是 |  | len 1-64 |
| slotsFree | integer | 是 |  | 0.0-256.0 |
| runningJobIds | string[] | 否 |  | items <= 256 |
| meta | Meta | 否 |  |  |

**响应：**
- Schema: `ApiResponse_WorkerAckData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| accepted | boolean | 否 |  |  |

### 15.2 Poll

**请求 URL：** `POST /api/workers/poll`

**鉴权：** 需要（worker token）

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| workerId | string | 是 |  | len 1-64 |
| capabilities | string[] | 是 |  | items 1-16 |

**响应：**
- Schema: `ApiResponse_WorkerPollData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| job | JobPayload \| null | 否 |  |  |
| sleepMs | integer | 否 |  | 200.0-60000.0 |

### 15.3 Register

**请求 URL：** `POST /api/workers/register`

**鉴权：** 无（需要 X-Tenant-Id）

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| X-Tenant-Id | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| name | string | 是 |  | len 1-255 |
| capabilities | string[] | 是 |  | items 1-16 |
| slots | integer | 是 |  | 1.0-256.0 |
| version | string | 是 |  | len 1-32 |

**响应：**
- Schema: `ApiResponse_WorkerRegisterData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| workerId | string | 是 |  | len 1-64 |
| token | string | 是 |  | len 1-256 |

### 15.4 Report

**请求 URL：** `POST /api/workers/report`

**鉴权：** 需要（worker token）

**请求头：**
| Header | 类型 | 必填 | 说明 | 约束 |
|------|--|--|--|--|
| Authorization | string \| null | 否 |  |  |

**请求体（JSON）：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| workerId | string | 是 |  | len 1-64 |
| jobId | string | 是 |  | len 1-64 |
| runId | string | 是 |  | len 1-64 |
| results | CaseRunResult[] | 是 |  | items 1-10000 |
| jobStatus | JobStatus | 是 |  |  |

**响应：**
- Schema: `ApiResponse_WorkerAckData_`

**响应 data：**
| 字段 | 类型 | 必填 | 说明 | 约束 |
|--|--|--|--|--|
| accepted | boolean | 否 |  |  |
