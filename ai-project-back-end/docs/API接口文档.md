# API 接口文档（后端）

基于代码仓库 `app/api` 与 `app/schemas` 生成；接口前缀见 [config.py](file:///d:/trae包/ai-project-back-end/app/core/config.py#L11-L21)（`api_prefix="/api"`）。

## 1. 通用约定

### 1.1 Base URL

- 接口统一前缀：`/api`
- 健康检查：`/health`（不带 `/api` 前缀）

### 1.2 统一返回体

除健康检查外，接口统一返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "requestId": "req_xxxxxxxxxxxxxxxx"
}
```

字段说明（[common.py](file:///d:/trae包/ai-project-back-end/app/schemas/common.py#L10-L25)）：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | int | 是 | 业务码；0 表示成功 |
| message | string | 是 | 提示信息；成功时默认 `ok` |
| data | object/null | 否 | 业务数据；不同接口不同 |
| requestId | string | 是 | 请求追踪 ID（最长 64） |

### 1.3 错误码与 HTTP 状态

服务端在发生异常时，仍可能返回 **HTTP 200**，通过 `code/message` 表达错误（见 [main.py](file:///d:/trae包/ai-project-back-end/app/main.py#L42-L70)）。状态码映射如下：

| 触发的 HTTP 状态 | code |
| --- | --- |
| 400 / 422 | 40001（参数校验失败） |
| 401 | 40101（未登录/鉴权失败） |
| 403 | 40301（无权限） |
| 404 | 40401（资源不存在） |
| 409 | 40901（版本冲突） |
| 429 | 42901（请求过频） |
| 503 | 50301（依赖服务不可用/DB 不可用） |
| 其他 | 50001（服务内部错误） |

参数校验失败时 `data.errors` 结构来自 FastAPI/Pydantic 的 `RequestValidationError.errors()`（见 [main.py](file:///d:/trae包/ai-project-back-end/app/main.py#L72-L83)）。

### 1.4 RequestId 生成规则

服务端优先从请求头读取（见 [deps.py](file:///d:/trae包/ai-project-back-end/app/api/deps.py#L21-L26)）：

| Header | 必填 | 说明 |
| --- | --- | --- |
| X-Request-Id / X-RequestId | 否 | 传入则回传（截断至 64）；不传则服务端生成 `req_` 开头 ID |

## 2. 鉴权

除 `/health`、`/api/auth/login`、`/api/auth/register` 外，其余接口均依赖 `get_current_user`（见 [deps.py](file:///d:/trae包/ai-project-back-end/app/api/deps.py#L28-L55)）。

支持两种方式：

1) Bearer Token：

| Header | 必填 | 说明 |
| --- | --- | --- |
| Authorization | 是 | `Bearer <accessToken>`，token 由 `/api/auth/login` 获取 |

2) 网关透传用户信息（无 Authorization 时启用）：

| Header | 必填 | 说明 |
| --- | --- | --- |
| X-User-Id | 是 | 当前用户 UUID |
| X-Tenant-Id | 是 | 当前租户 UUID |
| X-Roles | 否 | 角色列表，逗号分隔，例如 `ADMIN,OWNER` |

## 3. 通用类型与枚举

### 3.1 通用类型

见 [types.py](file:///d:/trae包/ai-project-back-end/app/schemas/types.py#L7-L23)：

| 类型别名 | 实际类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| IdStr | string | 1~64 | 通用 ID 字符串（业务上常为 UUID 字符串） |
| UnixTs | int | >= 0 | Unix 时间戳（秒） |
| NameStr | string | 1~255 | 名称 |
| TitleStr | string | 1~100 | 标题 |
| UrlStr | string | 1~2048 | URL |
| VersionStr | string | 1~32 | 版本字符串 |
| EmailStr | string | 3~255，需匹配邮箱正则 | 邮箱 |

### 3.2 枚举值

见 [enums.py](file:///d:/trae包/ai-project-back-end/app/models/enums.py#L16-L65)：

| 枚举 | 可选值 |
| --- | --- |
| TestCaseType | `API` `UI` `PERF` `MIX` |
| Priority | `P0` `P1` `P2` `P3` |
| TestCaseStatus | `DRAFT` `REVIEWED` `DEPRECATED` |
| TriggerType | `MANUAL` `CRON` `CI` `WEBHOOK` |
| RunStatus | `QUEUED` `RUNNING` `PASSED` `FAILED` `CANCELED` |
| CaseRunStatus | `QUEUED` `RUNNING` `PASSED` `FAILED` `SKIPPED` |

## 4. 接口明细

以下路径均以 `Base URL` 为准。

### 4.1 Health

#### 4.1.1 健康检查

- **URL**：`GET /health`
- **鉴权**：否
- **响应**：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| status | string | 是 | 固定为 `ok`（DB 可用时） |

---

### 4.2 Auth

#### 4.2.1 注册

- **URL**：`POST /api/auth/register`
- **鉴权**：否
- **Body**：[RegisterRequest](file:///d:/trae包/ai-project-back-end/app/schemas/auth.py#L11-L29)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| phone | string | 是 | 11~20；正则 `^1[3-9]\d{9}$` | 手机号 |
| username | string | 是 | 3~64 | 用户名 |
| password | string | 是 | 8~128；需同时包含字母与数字 | 密码 |
| confirmPassword | string | 是 | 8~128；需与 password 相同 | 确认密码 |
| captcha | string | 是 | 1~16 | 验证码 |

- **响应**：`ApiResponse<RegisterResponseData>`
- **data**：[RegisterResponseData](file:///d:/trae包/ai-project-back-end/app/schemas/auth.py#L32-L37)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| userId | string(IdStr) | 是 | 用户 ID |
| phone | string | 是 | 手机号 |
| username | string | 是 | 用户名 |
| createdAt | int(UnixTs) | 是 | 创建时间（秒） |

#### 4.2.2 登录

- **URL**：`POST /api/auth/login`
- **鉴权**：否
- **Body**：[LoginRequest](file:///d:/trae包/ai-project-back-end/app/schemas/auth.py#L39-L42)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| username | string | 是 | 1~255 | 用户名（代码变量名为 username_or_email，但字段名为 username） |
| password | string | 是 | 1~128 | 密码 |

- **响应**：`ApiResponse<LoginResponseData>`
- **data**：[LoginResponseData](file:///d:/trae包/ai-project-back-end/app/schemas/auth.py#L44-L47)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| accessToken | string | 是 | 访问 token |
| expiresIn | int | 是 | 有效期（秒） |

#### 4.2.3 退出登录

- **URL**：`POST /api/auth/logout`
- **鉴权**：是
- **响应**：`ApiResponse<LogoutResponseData>`
- **data**：[LogoutResponseData](file:///d:/ai-project/ai-project-back-end/app/schemas/auth.py#L49-L50)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| success | bool | 是 | 固定为 `true` |

#### 4.2.4 获取当前用户

- **URL**：`GET /api/auth/me`
- **鉴权**：是
- **响应**：`ApiResponse<MeResponseData>`
- **data**：[MeResponseData](file:///d:/ai-project/ai-project-back-end/app/schemas/auth.py#L53-L60)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| userId | string(IdStr) | 是 | 用户 ID |
| email | string(EmailStr)/null | 否 | 邮箱 |
| phone | string/null | 否 | 手机号 |
| username | string/null | 否 | 用户名 |
| name | string(NameStr) | 是 | 显示名 |
| roles | string[] | 是 | 角色列表 |
| tenantId | string(IdStr) | 是 | 租户 ID |

---

### 4.3 Projects

#### 4.3.1 创建项目

- **URL**：`POST /api/projects`
- **鉴权**：是
- **Body**：[ProjectCreateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/project.py#L9-L17)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| name | string(NameStr) | 是 | 1~255 | 项目名称 |
| description | string/null | 否 | <=2000；支持多个别名：`Description/desc/remark/projectDescription/projectDesc` | 项目描述 |
| ownerId | string(IdStr) | 是 | 1~64；服务端会校验为 UUID | 项目所有者 ID |

- **响应**：`ApiResponse<ProjectDetailData>`
- **data**：[ProjectDetailData](file:///d:/trae包/ai-project-back-end/app/schemas/project.py#L47-L53)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 项目 ID |
| name | string(NameStr) | 是 | 项目名称 |
| description | string/null | 否 | 项目描述 |
| ownerId | string(IdStr) | 是 | 项目所有者 ID |
| memberCount | int | 是 | 成员数 |
| createdAt | int(UnixTs) | 是 | 创建时间（秒） |

#### 4.3.2 项目列表/查询

- **URL**：`GET /api/projects`
- **鉴权**：是
- **Query**（见 [projects.py](file:///d:/trae包/ai-project-back-end/app/api/v1/endpoints/projects.py#L63-L90)）

| 参数 | 类型 | 必填 | 默认值 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- | --- |
| page | int | 否 | 1 | - | 页码 |
| pageSize | int | 否 | 20 | - | 每页数量 |
| keyword | string/null | 否 | - | - | 关键字 |
| key | string/null | 否 | - | 若 keyword 为空且 key 存在，则 keyword=key | keyword 兼容字段 |
| id | string/null | 否 | - | 若传入，则按项目 ID 精确查询并返回单条 | 项目 ID |

- **响应**：`ApiResponse<PageData<ProjectListItem>>`
- **data.items**：[ProjectListItem](file:///d:/trae包/ai-project-back-end/app/schemas/project.py#L35-L41)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 项目 ID |
| name | string(NameStr) | 是 | 项目名称 |
| ownerId | string(IdStr) | 是 | 项目所有者 ID |
| memberCount | int | 是 | 成员数 |
| createdAt | int(UnixTs) | 是 | 创建时间（秒） |

#### 4.3.3 获取项目详情

- **URL**：`GET /api/projects/{id}`
- **鉴权**：是
- **Path**：

| 参数 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | uuid | 是 | 项目 ID |

- **响应**：`ApiResponse<ProjectDetailData>`（字段同 4.3.1）

#### 4.3.4 更新项目（Path 方式）

- **URL**：`PUT /api/projects/{id}`
- **鉴权**：是
- **Path**：`id`（同 4.3.3）
- **Body**：[ProjectUpdateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/project.py#L19-L27)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| name | string(NameStr)/null | 否 | 1~255 | 项目名称 |
| description | string/null | 否 | <=2000；支持多个别名（同创建） | 项目描述 |
| ownerId | string(IdStr)/null | 否 | 1~64；若传入则校验为 UUID | 项目所有者 ID |

- **响应**：`ApiResponse<ProjectDetailData>`（字段同 4.3.1）

#### 4.3.5 更新项目（Query 方式）

- **URL**：`PUT /api/projects?id={uuid}`
- **鉴权**：是
- **Query**：

| 参数 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | uuid | 是 | 项目 ID |

- **Body/响应**：同 4.3.4

#### 4.3.6 删除项目（Path 方式）

- **URL**：`DELETE /api/projects/{id}`
- **鉴权**：是
- **Path**：`id`（同 4.3.3）
- **响应**：`ApiResponse<dict>`，data 固定为 `{}`（见 [projects.py](file:///d:/trae包/ai-project-back-end/app/api/v1/endpoints/projects.py#L155-L168)）

#### 4.3.7 删除项目（Query 方式）

- **URL**：`DELETE /api/projects?id={uuid}`
- **鉴权**：是
- **Query**：`id`（同 4.3.5）
- **响应**：同 4.3.6

---

### 4.4 Testcases

#### 4.4.1 创建用例

- **URL**：`POST /api/testcases`
- **鉴权**：是
- **Body**：[TestCaseCreateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/testcase.py#L16-L24)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| projectId | string(IdStr) | 是 | - | 项目 ID |
| title | string(TitleStr) | 是 | 1~100 | 用例标题 |
| type | enum(TestCaseType) | 是 | - | 用例类型 |
| priority | enum(Priority) | 是 | - | 优先级 |
| status | enum(TestCaseStatus) | 是 | - | 状态 |
| tags | string[] | 否 | <=50；单项 1~64 | 标签 |
| contentMd | string | 是 | min_length=1 | Markdown 内容 |

- **响应**：`ApiResponse<TestCaseDetail>`
- **data**：[TestCaseDetail](file:///d:/trae包/ai-project-back-end/app/schemas/testcase.py#L63-L74)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 用例 ID |
| projectId | string(IdStr) | 是 | 项目 ID |
| title | string(TitleStr) | 是 | 用例标题 |
| type | enum(TestCaseType) | 是 | 用例类型 |
| priority | enum(Priority) | 是 | 优先级 |
| status | enum(TestCaseStatus) | 是 | 状态 |
| tags | string[] | 是 | 标签 |
| ownerId | string(IdStr)/null | 否 | 负责人 ID |
| version | string | 是 | 版本字符串（正则 `^(?:v?1(?:\.\d+)?)$`） |
| contentMd | string | 是 | Markdown 内容 |

#### 4.4.2 用例列表

- **URL**：`GET /api/testcases`
- **鉴权**：是
- **Query**（见 [testcases.py](file:///d:/trae包/ai-project-back-end/app/api/v1/endpoints/testcases.py#L67-L80)）

| 参数 | 类型 | 必填 | 默认值 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- | --- |
| projectId | string | 是 | - | 会被解析为 UUID | 项目 ID |
| title | string/null | 否 | - | 1~100 | 标题过滤 |
| type | enum(TestCaseType)/null | 否 | - | - | 类型过滤 |
| status | enum(TestCaseStatus)/null | 否 | - | - | 状态过滤 |
| tag | string/null | 否 | - | - | 标签过滤 |
| ownerId | string/null | 否 | - | 会被解析为 UUID | 负责人过滤 |
| page | int | 否 | 1 | >=1 | 页码 |
| pageSize | int | 否 | 20 | 1~200 | 每页数量 |

- **响应**：`ApiResponse<PageData<TestCaseListItem>>`
- **data.items**：[TestCaseListItem](file:///d:/trae包/ai-project-back-end/app/schemas/testcase.py#L85-L95)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 用例 ID |
| projectId | string(IdStr) | 是 | 项目 ID |
| title | string(TitleStr) | 是 | 用例标题 |
| type | enum(TestCaseType) | 是 | 类型 |
| priority | enum(Priority) | 是 | 优先级 |
| status | enum(TestCaseStatus) | 是 | 状态 |
| tags | string[] | 是 | 标签 |
| ownerId | string(IdStr)/null | 否 | 负责人 |
| version | string | 是 | 版本 |

#### 4.4.3 获取用例详情

- **URL**：`GET /api/testcases/{id}`
- **鉴权**：是
- **Path**：`id: uuid`
- **响应**：`ApiResponse<TestCaseDetail>`（字段同 4.4.1）

#### 4.4.4 更新用例（Path 方式，全量）

- **URL**：`PUT /api/testcases/{id}`
- **鉴权**：是
- **Path**：`id: uuid`
- **Body**：[TestCasePutRequest](file:///d:/trae包/ai-project-back-end/app/schemas/testcase.py#L37-L46)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| projectId | string(IdStr) | 是 | - | 项目 ID |
| title | string(TitleStr) | 是 | 1~100 | 标题 |
| type | enum(TestCaseType) | 是 | - | 类型 |
| priority | enum(Priority) | 是 | - | 优先级 |
| status | enum(TestCaseStatus) | 是 | - | 状态 |
| tags | string[] | 否 | <=50；单项 1~64 | 标签 |
| contentMd | string | 是 | min_length=1 | Markdown 内容 |
| ownerId | string(IdStr)/null | 否 | - | 负责人 ID |

- **响应**：`ApiResponse<TestCaseDetail>`（字段同 4.4.1）

#### 4.4.5 更新用例（Query 方式）

- **URL**：`PUT /api/testcases?id={uuid}`
- **鉴权**：是
- **Query**：`id: uuid`
- **Body/响应**：同 4.4.4

#### 4.4.6 删除用例

- **URL**：`DELETE /api/testcases/{id}`
- **鉴权**：是
- **Path**：`id: uuid`
- **响应**：`ApiResponse<dict>`，data 固定为 `{}`

#### 4.4.7 用例版本列表--未使用

- **URL**：`GET /api/testcases/{id}/versions`
- **鉴权**：是
- **Path**：`id: uuid`
- **响应**：`ApiResponse<TestCaseVersionSchema[]>`
- **data item**：[TestCaseVersionSchema](file:///d:/trae包/ai-project-back-end/app/schemas/testcase.py#L76-L83)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 版本记录 ID |
| testcaseId | string(IdStr) | 是 | 用例 ID |
| version | string | 是 | 版本 |
| contentMd | string | 是 | Markdown 内容 |
| createdAt | int | 是 | 创建时间（秒） |
| createdBy | string(IdStr)/null | 否 | 创建人 |

#### 4.4.8 恢复用例到指定版本---未使用

- **URL**：`POST /api/testcases/{id}/restore`
- **鉴权**：是
- **Path**：`id: uuid`
- **Body**：[TestCaseRestoreRequest](file:///d:/trae包/ai-project-back-end/app/schemas/testcase.py#L48-L50)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| version | string | 是 | 正则 `^(?:v?1(?:\.\d+)?)$` | 目标版本 |

- **响应**：`ApiResponse<TestCaseDetail>`（字段同 4.4.1）

---

### 4.5 Suites

#### 4.5.1 创建套件

- **URL**：`POST /api/suites`
- **鉴权**：是
- **Body**：[SuiteCreateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/suite.py#L19-L24)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| projectId | string(IdStr) | 是 | - | 项目 ID |
| name | string(NameStr) | 是 | 1~255 | 套件名称 |
| defaultEnvId | string(IdStr)/null | 否 | - | 默认环境 ID |
| config | object | 是 | - | 套件配置（见下） |

`config` 字段：[SuiteConfig](file:///d:/trae包/ai-project-back-end/app/schemas/suite.py#L10-L17)

| 字段 | 类型 | 必填 | 默认值 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- | --- |
| timeoutSec | int | 否 | 600 | 1~86400 | 超时时间（秒） |
| concurrency | int | 否 | 4 | 1~256 | 并发 |
| retryCount | int | 否 | 1 | 0~20 | 重试次数 |
| retryOnlyOn | string[] | 否 | `["NETWORK","TIMEOUT","FLAKE"]` | <=32 | 仅在这些错误类型重试 |
| failFast | bool | 否 | false | - | 失败快速终止 |
| variables | object | 否 | {} | - | 变量字典（string->string） |

- **响应**：`ApiResponse<SuitePublic>`
- **data**：[SuitePublic](file:///d:/trae包/ai-project-back-end/app/schemas/suite.py#L43-L51)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 套件 ID |
| projectId | string(IdStr) | 是 | 项目 ID |
| name | string(NameStr) | 是 | 套件名称 |
| defaultEnvId | string(IdStr)/null | 否 | 默认环境 |
| config | object | 是 | 套件配置 |
| createdAt | int(UnixTs) | 是 | 创建时间（秒） |
| updatedAt | int(UnixTs) | 是 | 更新时间（秒） |

#### 4.5.2 套件列表

- **URL**：`GET /api/suites`
- **鉴权**：是
- **Query**（见 [suites.py](file:///d:/trae包/ai-project-back-end/app/api/v1/endpoints/suites.py#L92-L100)）

| 参数 | 类型 | 必填 | 默认值 | 注释 |
| --- | --- | --- | --- | --- |
| projectId | string/null | 否 | - | 项目 ID（UUID 字符串） |
| page | int | 否 | 1 | 页码 |
| pageSize | int | 否 | 20 | 每页数量（1~200） |

- **响应**：`ApiResponse<PageData<SuitePublic>>`（items 字段同 4.5.1）

#### 4.5.3 获取套件详情

- **URL**：`GET /api/suites/{id}`
- **鉴权**：是
- **Path**：`id: uuid`
- **响应**：`ApiResponse<SuitePublic>`（字段同 4.5.1）

#### 4.5.4 更新套件

- **URL**：`PUT /api/suites/{id}`
- **鉴权**：是
- **Path**：`id: uuid`
- **Body**：[SuitePutRequest](file:///d:/trae包/ai-project-back-end/app/schemas/suite.py#L26-L31)（字段同创建）
- **响应**：`ApiResponse<SuitePublic>`（字段同 4.5.1）

#### 4.5.5 删除套件

- **URL**：`DELETE /api/suites/{id}`
- **鉴权**：是
- **Path**：`id: uuid`
- **响应**：`ApiResponse<dict>`，data 固定为 `{}`

#### 4.5.6 批量写入套件用例项（Upsert）

- **URL**：`POST /api/suites/{suiteId}/items`
- **鉴权**：是
- **Path**：

| 参数 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| suiteId | uuid | 是 | 套件 ID |

- **Body**：[SuiteItemsUpsertRequest](file:///d:/trae包/ai-project-back-end/app/schemas/suite.py#L39-L41)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| items | object[] | 是 | 1~10000 | 套件用例列表 |

items 元素：[SuiteItemInput](file:///d:/trae包/ai-project-back-end/app/schemas/suite.py#L33-L37)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| testcaseId | string(IdStr) | 是 | - | 用例 ID |
| orderNo | int | 是 | >=1 | 排序号 |
| params | object | 否 | - | 参数字典 |

- **响应**：`ApiResponse<SuiteItemPublic[]>`
- **data item**：[SuiteItemPublic](file:///d:/trae包/ai-project-back-end/app/schemas/suite.py#L61-L70)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 记录 ID |
| suiteId | string(IdStr) | 是 | 套件 ID |
| testcaseId | string(IdStr) | 是 | 用例 ID |
| orderNo | int | 是 | 排序号 |
| params | object | 是 | 参数 |
| testcaseTitle | string(TitleStr) | 是 | 用例标题 |
| testcaseType | enum(TestCaseType) | 是 | 用例类型 |
| testcasePriority | enum(Priority) | 是 | 优先级 |
| testcaseStatus | enum(TestCaseStatus) | 是 | 状态 |

#### 4.5.7 获取套件用例项列表

- **URL**：`GET /api/suites/{suiteId}/items`
- **鉴权**：是
- **Path**：`suiteId: uuid`
- **响应**：`ApiResponse<SuiteItemPublic[]>`（字段同 4.5.6）

---

### 4.6 Environments

接口前缀：`/api/projects/{projectId}/environments`（见 [environments.py](file:///d:/trae包/ai-project-back-end/app/api/v1/endpoints/environments.py#L22-L40)）。

#### 4.6.1 创建环境

- **URL**：`POST /api/projects/{projectId}/environments`
- **鉴权**：是
- **Path**：`projectId: uuid`
- **Body**：[EnvironmentCreateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/environment.py#L15-L21)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| name | string(NameStr) | 是 | 环境名称 |
| baseUrl | string(UrlStr) | 是 | 基础 URL |
| variables | object | 否 | 变量字典（string->string） |
| secrets | object | 否 | 密钥字典（string->string；写入后不会在读取时回显 value） |
| healthCheck | object/null | 否 | 健康检查配置（见下） |

healthCheck：[HealthCheckConfig](file:///d:/trae包/ai-project-back-end/app/schemas/environment.py#L9-L13)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| url | string(UrlStr) | 是 | - | 探测 URL |
| timeoutMs | int | 是 | 1~60000 | 超时毫秒 |
| expectedStatus | int | 是 | 100~599 | 期望 HTTP 状态码 |

- **响应**：`ApiResponse<EnvironmentPublic>`
- **data**：[EnvironmentPublic](file:///d:/trae包/ai-project-back-end/app/schemas/environment.py#L31-L40)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 环境 ID |
| projectId | string(IdStr) | 是 | 项目 ID |
| name | string(NameStr) | 是 | 环境名称 |
| baseUrl | string(UrlStr) | 是 | 基础 URL |
| variables | object | 是 | 变量字典 |
| secretKeys | string[] | 是 | 仅返回 secret 的 key 列表 |
| healthCheck | object/null | 否 | 健康检查配置 |
| createdAt | int(UnixTs)/null | 否 | 创建时间（秒） |
| updatedAt | int(UnixTs)/null | 否 | 更新时间（秒） |

#### 4.6.2 环境列表

- **URL**：`GET /api/projects/{projectId}/environments`
- **鉴权**：是
- **Path**：`projectId: uuid`
- **响应**：`ApiResponse<EnvironmentPublic[]>`

#### 4.6.3 获取环境详情

- **URL**：`GET /api/projects/{projectId}/environments/{envId}`
- **鉴权**：是
- **Path**：`projectId: uuid`，`envId: uuid`
- **响应**：`ApiResponse<EnvironmentPublic>`

#### 4.6.4 更新环境（局部更新）

- **URL**：`PUT /api/projects/{projectId}/environments/{envId}`
- **鉴权**：是
- **Path**：`projectId: uuid`，`envId: uuid`
- **Body**：[EnvironmentUpdateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/environment.py#L23-L29)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| name | string(NameStr)/null | 否 | - | 环境名称 |
| baseUrl | string(UrlStr)/null | 否 | - | 基础 URL |
| variables | object/null | 否 | - | 变量字典 |
| secrets | object/null | 否 | - | 密钥字典 |
| healthCheck | object/null | 否 | - | 传 `null` 表示清空健康检查 |

- **响应**：`ApiResponse<EnvironmentPublic>`

#### 4.6.5 删除环境

- **URL**：`DELETE /api/projects/{projectId}/environments/{envId}`
- **鉴权**：是
- **响应**：`ApiResponse<dict>`，data 固定为 `{}`

---

### 4.7 Runs

#### 4.7.1 创建运行（触发执行）

- **URL**：`POST /api/runs`
- **鉴权**：是
- **Headers**（见 [runs.py](file:///d:/trae包/ai-project-back-end/app/api/v1/endpoints/runs.py#L39-L50)）：

| Header | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- |
| Idempotency-Key | 否 | 会被 trim 并截断至 128 | 幂等键 |

- **Body**：[RunCreateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/run.py#L10-L17)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| projectId | string(IdStr) | 是 | 项目 ID |
| suiteId | string(IdStr) | 是 | 套件 ID |
| envId | string(IdStr) | 是 | 环境 ID |
| triggerType | enum(TriggerType) | 是 | 触发方式 |
| meta | object | 否 | 附加信息 |
| notifyRuleId | string(IdStr)/null | 否 | 通知规则 ID |

- **响应**：`ApiResponse<RunDetailData>`
- **data**：[RunDetailData](file:///d:/trae包/ai-project-back-end/app/schemas/run.py#L24-L31)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | run ID |
| status | enum(RunStatus) | 是 | 状态 |
| progress | object | 是 | 进度（done/total） |
| suiteId | string(IdStr) | 是 | 套件 ID |
| envId | string(IdStr) | 是 | 环境 ID |
| startAt | int(UnixTs) | 是 | 开始时间（秒） |

progress：[RunProgress](file:///d:/trae包/ai-project-back-end/app/schemas/run.py#L19-L22)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| done | int | 是 | 已完成用例数 |
| total | int | 是 | 总用例数 |

#### 4.7.2 运行列表

- **URL**：`GET /api/runs`
- **鉴权**：是
- **Query**（见 [runs.py](file:///d:/trae包/ai-project-back-end/app/api/v1/endpoints/runs.py#L71-L82)）

| 参数 | 类型 | 必填 | 默认值 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- | --- |
| projectId | string/null | 否 | - | 传入时需为 UUID 字符串 | 项目 ID |
| status | enum(RunStatus)/null | 否 | - | - | 状态过滤 |
| from | int/null | 否 | - | query 名为 `from`（别名） | 开始时间下界（秒） |
| to | int/null | 否 | - | - | 开始时间上界（秒） |
| page | int | 否 | 1 | >=1 | 页码 |
| pageSize | int | 否 | 20 | 1~200 | 每页数量 |

- **响应**：`ApiResponse<PageData<RunDetailData>>`（items 字段同 4.7.1）

#### 4.7.3 运行详情

- **URL**：`GET /api/runs/{runId}`
- **鉴权**：是
- **Path**：`runId: uuid`
- **响应**：`ApiResponse<RunDetailData>`

#### 4.7.4 CaseRun 列表

- **URL**：`GET /api/runs/{runId}/case-runs`
- **鉴权**：是
- **Path**：`runId: uuid`
- **Query**（见 [runs.py](file:///d:/trae包/ai-project-back-end/app/api/v1/endpoints/runs.py#L115-L124)）

| 参数 | 类型 | 必填 | 默认值 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- | --- |
| status | enum(CaseRunStatus)/null | 否 | - | - | 状态过滤 |
| page | int | 否 | 1 | >=1 | 页码 |
| pageSize | int | 否 | 50 | 1~200 | 每页数量 |

- **响应**：`ApiResponse<PageData<CaseRunListItem>>`
- **data.items**：[CaseRunListItem](file:///d:/trae包/ai-project-back-end/app/schemas/run.py#L70-L78)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| caseRunId | string(IdStr) | 是 | caseRun ID |
| testcaseId | string(IdStr) | 是 | 用例 ID |
| status | enum(CaseRunStatus) | 是 | 状态 |
| startAt | int(UnixTs)/null | 否 | 开始时间（秒） |
| endAt | int(UnixTs)/null | 否 | 结束时间（秒） |
| errorType | string/null | 否 | 错误类型（<=64） |
| errorMessage | string/null | 否 | 错误信息（<=2000） |

#### 4.7.5 取消运行

- **URL**：`POST /api/runs/{runId}/cancel`
- **鉴权**：是
- **Path**：`runId: uuid`
- **响应**：`ApiResponse<RunCancelResponseData>`
- **data**：[RunCancelResponseData](file:///d:/trae包/ai-project-back-end/app/schemas/run.py#L84-L87)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| runId | string(IdStr) | 是 | run ID |
| status | enum(RunStatus) | 是 | 更新后的状态 |

#### 4.7.6 重试运行

- **URL**：`POST /api/runs/{runId}/retry`
- **鉴权**：是
- **Path**：`runId: uuid`
- **Headers**：`Idempotency-Key`（同 4.7.1）
- **Body**：[RunRetryRequest](file:///d:/trae包/ai-project-back-end/app/schemas/run.py#L89-L91)

| 字段 | 类型 | 必填 | 默认值 | 注释 |
| --- | --- | --- | --- | --- |
| failedOnly | bool | 否 | true | 仅重试失败用例 |

- **响应**：`ApiResponse<RunDetailData>`（字段同 4.7.1）

---

### 4.8 Collections（API 集合）

#### 4.8.1 集合列表

- **URL**：`GET /api/collections`
- **鉴权**：是
- **Query**（见 [collections.py](file:///d:/trae包/ai-project-back-end/app/api/v1/endpoints/collections.py#L75-L83)）

| 参数 | 类型 | 必填 | 默认值 | 注释 |
| --- | --- | --- | --- | --- |
| projectId | string | 是 | - | 项目 ID（UUID 字符串） |
| page | int | 否 | 1 | 页码 |
| pageSize | int | 否 | 20 | 每页数量（1~200） |

- **响应**：`ApiResponse<PageData<CollectionListItem>>`
- **data.items**：[CollectionListItem](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L9-L15)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 集合 ID |
| projectId | string(IdStr) | 是 | 项目 ID |
| name | string(NameStr) | 是 | 集合名称 |
| requestCount | int | 是 | 请求数 |
| updatedAt | int(UnixTs) | 是 | 更新时间（秒） |

#### 4.8.2 创建集合

- **URL**：`POST /api/collections`
- **鉴权**：是
- **Body**：[CollectionCreateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L17-L21)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| projectId | string(IdStr) | 是 | 项目 ID |
| name | string(NameStr) | 是 | 集合名称 |
| variables | object | 否 | 集合级变量字典 |

- **响应**：`ApiResponse<ApiCollectionDetail>`
- **data**：[ApiCollectionDetail](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L53-L61)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 集合 ID |
| projectId | string(IdStr) | 是 | 项目 ID |
| name | string(NameStr) | 是 | 集合名称 |
| variables | object | 是 | 变量字典 |
| groups | object[] | 是 | 分组（含 requests） |
| requests | object[] | 是 | 未分组请求 |
| updatedAt | int(UnixTs) | 是 | 更新时间（秒） |

groups 元素：[ApiCollectionGroupWithRequests](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L49-L51)，requests 元素：[ApiRequestPublic](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L28-L40)

#### 4.8.3 获取集合详情

- **URL**：`GET /api/collections/{collectionId}`
- **鉴权**：是
- **Path**：`collectionId: uuid`
- **响应**：`ApiResponse<ApiCollectionDetail>`（字段同 4.8.2）

#### 4.8.4 更新集合（局部更新）

- **URL**：`PUT /api/collections/{collectionId}`
- **鉴权**：是
- **Path**：`collectionId: uuid`
- **Body**：[CollectionUpdateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L23-L26)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| name | string(NameStr)/null | 否 | 集合名称 |
| variables | object/null | 否 | 变量字典；是否更新由字段是否出现在请求体中决定 |

- **响应**：`ApiResponse<ApiCollectionDetail>`（字段同 4.8.2）

#### 4.8.5 删除集合

- **URL**：`DELETE /api/collections/{collectionId}`
- **鉴权**：是
- **Path**：`collectionId: uuid`
- **响应**：`ApiResponse<dict>`，data 固定为 `{}`

#### 4.8.6 创建分组

- **URL**：`POST /api/collections/{collectionId}/groups`
- **鉴权**：是
- **Path**：`collectionId: uuid`
- **Body**：[GroupCreateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L63-L65)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| name | string(NameStr) | 是 | 分组名称 |

- **响应**：`ApiResponse<ApiCollectionGroupPublic>`
- **data**：[ApiCollectionGroupPublic](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L42-L47)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 分组 ID |
| collectionId | string(IdStr) | 是 | 集合 ID |
| name | string(NameStr) | 是 | 分组名称 |
| order | int | 是 | 排序值（>=0） |

#### 4.8.7 更新分组

- **URL**：`PUT /api/collections/{collectionId}/groups/{groupId}`
- **鉴权**：是
- **Path**：`collectionId: uuid`，`groupId: uuid`
- **Body**：[GroupUpdateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L67-L69)（字段同创建）
- **响应**：`ApiResponse<ApiCollectionGroupPublic>`（字段同 4.8.6）

#### 4.8.8 删除分组

- **URL**：`DELETE /api/collections/{collectionId}/groups/{groupId}`
- **鉴权**：是
- **响应**：`ApiResponse<dict>`，data 固定为 `{}`

#### 4.8.9 创建请求

- **URL**：`POST /api/collections/{collectionId}/requests`
- **鉴权**：是
- **Path**：`collectionId: uuid`
- **Body**：[ApiRequestCreateRequest](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L71-L80)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| groupId | string(IdStr)/null | 否 | 传入时需为 UUID 字符串 | 分组 ID |
| name | string(NameStr) | 是 | - | 请求名称 |
| method | string | 是 | 1~16 | HTTP 方法 |
| url | string(UrlStr) | 是 | - | 请求 URL（支持相对路径） |
| headers | object | 否 | - | 请求头 |
| auth | object | 否 | - | 鉴权信息（结构由导入/前端决定） |
| body | object | 否 | - | 请求体（结构由导入/前端决定） |
| asserts | object | 否 | - | 断言配置（结构由导入/前端决定） |

- **响应**：`ApiResponse<ApiRequestPublic>`
- **data**：[ApiRequestPublic](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L28-L40)（字段同创建，额外包含 `id/collectionId/updatedAt`）

#### 4.8.10 获取请求详情

- **URL**：`GET /api/collections/{collectionId}/requests/{requestId}`
- **鉴权**：是
- **Path**：`collectionId: uuid`，`requestId: uuid`
- **响应**：`ApiResponse<ApiRequestPublic>`

#### 4.8.11 更新请求

- **URL**：`PUT /api/collections/{collectionId}/requests/{requestId}`
- **鉴权**：是
- **Body**：同 4.8.9（复用 ApiRequestCreateRequest）
- **响应**：`ApiResponse<ApiRequestPublic>`

#### 4.8.12 删除请求

- **URL**：`DELETE /api/collections/{collectionId}/requests/{requestId}`
- **鉴权**：是
- **响应**：`ApiResponse<dict>`，data 固定为 `{}`

#### 4.8.13 导入集合

- **URL**：`POST /api/collections/import`
- **鉴权**：是
- **Body**：[ImportCollectionRequest](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L82-L86)

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| projectId | string(IdStr) | 是 | - | 项目 ID |
| format | string | 是 | 1~32；服务端仅支持 `postman` / `swagger` | 导入格式 |
| content | string | 是 | min_length=1 | 导入内容（JSON 字符串） |

- **响应**：`ApiResponse<ApiCollectionDetail>`（字段同 4.8.2）

#### 4.8.14 导出集合

- **URL**：`GET /api/collections/{collectionId}/export`
- **鉴权**：是
- **Path**：`collectionId: uuid`
- **Query**：

| 参数 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| format | string | 是 | 服务端支持 `postman` / `swagger` / `curl` | 导出格式 |

- **响应**：`ApiResponse<ExportCollectionData>`
- **data**：[ExportCollectionData](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L88-L91)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| format | string | 是 | 导出格式 |
| content | string | 是 | 导出内容（JSON / 文本） |

#### 4.8.15 快速运行整个集合

- **URL**：`POST /api/collections/{collectionId}/run`
- **鉴权**：是
- **Path**：`collectionId: uuid`
- **Body**：[RunCollectionRequest](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L93-L97)

| 字段 | 类型 | 必填 | 默认值 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- | --- |
| envId | string(IdStr)/null | 否 | - | 传入时需为 UUID 字符串 | 环境 ID |
| concurrency | int | 否 | 1 | 1~100 | 并发 |
| iterations | int | 否 | 1 | 1~1000 | 迭代次数 |

- **响应**：`ApiResponse<dict>`（结构由 [collection.py:run_collection_quick](file:///d:/trae包/ai-project-back-end/app/services/collection.py#L880-L934) 直接返回）

data 字段结构：

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| collectionId | string | 是 | 集合 ID |
| envId | string/null | 否 | 环境 ID |
| concurrency | int | 是 | 并发 |
| iterations | int | 是 | 迭代次数 |
| summary | object | 是 | 汇总（total/passed/failed） |
| results | object[] | 是 | 每个请求的执行结果（见 4.8.16） |

#### 4.8.16 快速运行单个请求

- **URL**：`POST /api/collections/{collectionId}/requests/{requestId}/run`
- **鉴权**：是
- **Path**：`collectionId: uuid`，`requestId: uuid`
- **Body**：[RunApiRequestRequest](file:///d:/trae包/ai-project-back-end/app/schemas/collection.py#L99-L100)

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| envId | string(IdStr)/null | 否 | 环境 ID（UUID 字符串） |

- **响应**：`ApiResponse<dict>`（结构由 [collection.py:run_request_quick](file:///d:/trae包/ai-project-back-end/app/services/collection.py#L814-L877) 直接返回）

data 字段结构：

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| collectionId | string | 是 | 集合 ID |
| requestId | string | 是 | 请求 ID |
| envId | string/null | 否 | 环境 ID |
| ok | bool | 是 | 是否通过（含状态码断言） |
| status | int/null | 否 | 实际 HTTP 状态码 |
| elapsedMs | int | 是 | 耗时毫秒 |
| error | string/null | 否 | 异常信息（网络/超时等） |
| response | object | 是 | 响应内容（headers/body） |

---

### 4.9 Dashboard（仪表盘）

以下接口用于仪表盘页面数据聚合，统一遵循 `ApiResponse` 返回体与鉴权约定。

#### 4.9.1 今日执行统计卡片

- **URL**：`GET /api/projects/{projectId}/dashboard/summary`
- **鉴权**：是
- **Path**：`projectId: uuid`
- **Query**：

| 参数 | 类型 | 必填 | 默认值 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- | --- |
| from | int(UnixTs)/null | 否 | 当日 00:00:00 | 与 to 组成统计窗口 | 起始时间（秒） |
| to | int(UnixTs)/null | 否 | 当日 23:59:59 | 与 from 组成统计窗口 | 结束时间（秒） |
| tz | string/null | 否 | `Asia/Shanghai` | 仅用于窗口边界换算 | 时区 |

- **响应**：`ApiResponse<dict>`

data 字段结构：

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| from | int(UnixTs) | 是 | 统计窗口开始时间 |
| to | int(UnixTs) | 是 | 统计窗口结束时间 |
| totalRuns | int | 是 | 运行总数 |
| passedRuns | int | 是 | 成功运行数 |
| failedRuns | int | 是 | 失败运行数 |
| runningRuns | int | 是 | 运行中数量 |
| canceledRuns | int | 是 | 已取消数量 |
| passRate | number | 是 | 通过率，0~100，保留 1 位小数 |
| updatedAt | int(UnixTs) | 是 | 指标生成时间 |

#### 4.9.2 近 7/14/30 天趋势

- **URL**：`GET /api/projects/{projectId}/dashboard/trend`
- **鉴权**：是
- **Path**：`projectId: uuid`
- **Query**：

| 参数 | 类型 | 必填 | 默认值 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- | --- |
| days | int | 否 | 7 | 仅支持 `7/14/30` | 时间窗口（天） |
| granularity | string | 否 | `day` | 当前固定 `day` | 聚合粒度 |
| tz | string/null | 否 | `Asia/Shanghai` | 用于自然日聚合 | 时区 |

- **响应**：`ApiResponse<dict>`

data 字段结构：

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| days | int | 是 | 时间窗口（天） |
| granularity | string | 是 | 聚合粒度 |
| items | object[] | 是 | 趋势数据点 |

items[] 元素结构：

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| bucketTs | int(UnixTs) | 是 | 时间桶起点（秒） |
| totalRuns | int | 是 | 当日运行总数 |
| failedRuns | int | 是 | 当日失败数 |
| passRate | number | 是 | 当日通过率 |

#### 4.9.3 失败 Top 榜单

- **URL**：`GET /api/projects/{projectId}/dashboard/failure-top`
- **鉴权**：是
- **Path**：`projectId: uuid`
- **Query**：

| 参数 | 类型 | 必填 | 默认值 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- | --- |
| dimension | string | 否 | `testcase` | 枚举：`testcase`、`suite` | 榜单维度 |
| days | int | 否 | 7 | 建议支持 `7/14/30` | 时间窗口（天） |
| limit | int | 否 | 10 | `1~50` | 返回条数 |

- **响应**：`ApiResponse<dict>`

data 字段结构：

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| dimension | string | 是 | 当前维度 |
| days | int | 是 | 时间窗口 |
| items | object[] | 是 | 失败榜单 |

items[] 通用字段：

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| id | string(IdStr) | 是 | 维度实体 ID |
| name | string | 是 | 维度实体名称 |
| failCount | int | 是 | 失败次数 |
| totalRuns | int | 是 | 总运行次数 |
| failRate | number | 是 | 失败率 |
| lastFailedAt | int(UnixTs)/null | 否 | 最近失败时间 |

当 `dimension=testcase` 时，items[] 额外字段：

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| flake | bool | 是 | 是否不稳定用例 |
| suiteNames | string[] | 否 | 所属套件名列表 |

#### 4.9.4 质量门禁状态（V1.1）

- **URL**：`GET /api/projects/{projectId}/dashboard/quality-gate`
- **鉴权**：是
- **Path**：`projectId: uuid`
- **响应**：`ApiResponse<dict>`

data 字段结构：

| 字段 | 类型 | 必填 | 约束/备注 | 注释 |
| --- | --- | --- | --- | --- |
| overall | string | 是 | 枚举：`PASSED` `PARTIAL_FAIL` `FAILED` `UNKNOWN` | 门禁总状态 |
| lastCheckedAt | int(UnixTs)/null | 否 | - | 最近检测时间 |
| linkedRunId | string(IdStr)/null | 否 | - | 关联运行 ID |
| gates | object[] | 是 | - | 子门禁结果 |

gates[] 元素结构：

| 字段 | 类型 | 必填 | 注释 |
| --- | --- | --- | --- |
| name | string | 是 | 规则名称 |
| threshold | string | 是 | 阈值描述 |
| current | string | 是 | 当前值描述 |
| passed | bool | 是 | 是否通过 |

#### 4.9.5 最近运行列表（复用 Runs）

- **URL**：`GET /api/runs?projectId={projectId}&page=1&pageSize=5`
- **鉴权**：是
- **说明**：复用 4.7.2，不新增接口；用于仪表盘右下角最近运行卡片。

#### 4.9.6 进行中 Run 实时状态（复用 Runs）

- **URL**：`GET /api/runs/{runId}`
- **鉴权**：是
- **说明**：复用 4.7.3，不新增接口；仪表盘前端建议每 5 秒轮询一次进行中 Run 状态。
