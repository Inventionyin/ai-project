# 统一方案：AI生成测试用例 + 用例挂载批量执行（可执行版）

## 1. 文档目标

本方案用于合并两份设计稿并消除冲突，形成可直接进入研发排期的执行文档：

- AI生成测试用例（PRD/Figma/HTML 导入）
- 测试用例界面挂载测试数据与接口并批量执行

适用范围：

- 后端 API、数据库、执行链路
- 前端 CasesPanel/CasesTable/运行弹窗/报告页
- 幂等、并发、错误码与兼容策略

---

## 2. 冲突检查结论（接口、数据库、状态机）

## 2.1 总体结论

两套方案可合并，**无不可解冲突**；存在 6 个需要统一口径的设计点。

## 2.2 冲突清单与统一决策

| 序号 | 领域 | 冲突点 | 风险 | 统一决策 |
|---|---|---|---|---|
| 1 | API 路由 | `POST /api/testcases/ai-import/jobs` 与已有 `/api/testcases/{id}` 动态路由共前缀 | 路由匹配歧义 | 采用独立子路由前缀：`/api/testcases/ai-import/*`，并在路由注册中优先注册静态路径 |
| 2 | 用例字段 vs 挂载字段 | AI方案在 `testcases` 增加 `api_url/api_method`；批量执行方案有 `api_targets` | 数据重复、来源不清 | `testcases.api_url/api_method` 仅作“展示与推荐默认值”；执行时以 `testcase_bindings + api_targets` 为准 |
| 3 | Run 返回结构 | 批量执行直连方案中 `suiteId` 可能无真实套件 | 影响现有 RunDetail 兼容 | 保留 `suiteId` 字段，直连执行写入固定逻辑套件ID（虚拟套件），并在 `summary_json.executionSource=TESTCASE_DIRECT` 标识来源 |
| 4 | 报告唯一约束 | AI方案 `reports` 表建议 `UNIQUE(run_id)` | 未来多报告类型扩展受限 | 调整为 `UNIQUE(run_id, report_type)` |
| 5 | 幂等规则 | 两方案都提幂等，但未统一适用接口 | 重复创建或误冲突 | 统一：所有创建型 POST（ai-import job、binding、api-target、from-testcases run）支持 `Idempotency-Key` |
| 6 | 状态枚举 | AI任务状态与运行状态并存 | 前端状态渲染混乱 | 分域管理：`ai_import_jobs.status` 与 `runs.status/case_runs.status` 各自独立，禁止复用枚举 |

---

## 3. 合并后总体架构

## 3.1 功能流

1. 用户在用例页发起 AI 导入任务（PRD/Figma/HTML）
2. 任务解析后预览候选用例，选择提交入库到 `testcases`
3. 用户在用例页为用例配置挂载（数据集 + 接口目标 + 参数）
4. 多选用例触发批量执行，生成 `runs/case_runs/jobs`
5. 运行完成后在报告页查看统计与 Allure 链接

## 3.2 数据主线

- 生成主线：`ai_import_jobs -> ai_import_items -> testcases`
- 执行主线：`testcases + testcase_bindings + api_targets + test_data_sets -> runs -> case_runs -> reports`

---

## 4. 统一 API 规范（字段级）

## 4.1 统一协议

- Header
  - `Authorization: Bearer <token>`
  - `X-Request-Id: <optional>`
  - `Idempotency-Key: <optional, 1..128>`
- 统一响应壳

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "requestId": "req_xxx"
}
```

## 4.2 AI 导入接口

### 4.2.1 创建任务

- `POST /api/testcases/ai-import/jobs`

```json
{
  "projectId": "2f1e8b15-5a0f-4df1-9f85-e7a8ed47a001",
  "sourceType": "FIGMA_LINK",
  "source": {
    "figmaUrl": "https://www.figma.com/file/AbCdEf123456/Checkout?node-id=100-200"
  },
  "generateConfig": {
    "language": "zh-CN",
    "maxCases": 80,
    "dedupeStrategy": "TITLE_STORY_URL",
    "defaultPriority": "P1",
    "defaultType": "API",
    "autoExtractApi": true
  },
  "skillConfig": {
    "enableFeature": true,
    "enableEpic": true,
    "enableStory": true,
    "enableTask": true,
    "enableDescription": true,
    "enableTitle": true,
    "enableStep": true
  }
}
```

### 4.2.2 上传文件

- `POST /api/testcases/ai-import/jobs/{jobId}/file`
- `multipart/form-data`：`file`、`filename`、`sourceType`

### 4.2.3 启动解析

- `POST /api/testcases/ai-import/jobs/{jobId}/start`

### 4.2.4 查询任务

- `GET /api/testcases/ai-import/jobs/{jobId}`
- 返回 `summary + previewItems[]`

### 4.2.5 提交入库

- `POST /api/testcases/ai-import/jobs/{jobId}/commit`

```json
{
  "selectedItemIds": [
    "f497f852-8a25-4da3-b1ec-79ac96f01a11",
    "f497f852-8a25-4da3-b1ec-79ac96f01a12"
  ],
  "saveAsStatus": "DRAFT",
  "ownerId": "8cfbe836-dbd8-411f-9c60-66fbd9f53a01"
}
```

## 4.3 挂载配置接口

### 4.3.1 接口目标（ApiTarget）

- `GET /api/api-targets?projectId={id}&page=1&pageSize=20`
- `POST /api/api-targets`
- `PUT /api/api-targets/{id}`
- `DELETE /api/api-targets/{id}`

关键字段：

- `name/baseUrl/defaultMethod/defaultPath/headers/authRef/timeoutMs/enabled/version`

### 4.3.2 用例绑定（TestcaseBinding）

- `GET /api/testcases/{testcaseId}/bindings?page=1&pageSize=20`
- `POST /api/testcases/{testcaseId}/bindings`
- `PUT /api/testcase-bindings/{bindingId}`
- `DELETE /api/testcase-bindings/{bindingId}`

关键字段：

- `datasetId`（可空）
- `apiTargetId`（可空）
- `params`（可空）
- `priority/enabled/version`

## 4.4 批量执行接口

### 4.4.1 用例直连批量执行

- `POST /api/runs/from-testcases`

```json
{
  "projectId": "prj_01",
  "envId": "env_01",
  "triggerType": "MANUAL",
  "meta": {
    "source": "cases_panel"
  },
  "concurrency": 10,
  "stopOnFailure": false,
  "items": [
    {
      "testcaseId": "tc_01",
      "bindingId": "tb_01"
    },
    {
      "testcaseId": "tc_02",
      "bindingId": "tb_09",
      "overrideParams": {
        "tenantCode": "t001"
      }
    }
  ],
  "notifyRuleId": "nr_01"
}
```

### 4.4.2 运行明细

- `GET /api/runs/{runId}/case-runs`
- 保持原字段，新增可选 `bindingSnapshot`

---

## 5. 数据库统一 DDL（执行版）

## 5.1 扩展 testcases

```sql
ALTER TABLE testcases
  ADD COLUMN feature VARCHAR(128),
  ADD COLUMN story VARCHAR(128),
  ADD COLUMN api_url VARCHAR(1024),
  ADD COLUMN api_method VARCHAR(16),
  ADD COLUMN ai_meta_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN generated_by_ai BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX ix_testcases_project_feature ON testcases(project_id, feature);
CREATE INDEX ix_testcases_project_story ON testcases(project_id, story);
CREATE INDEX ix_testcases_project_api_url ON testcases(project_id, api_url);
```

## 5.2 新增 AI 导入表

```sql
CREATE TABLE ai_import_jobs (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  project_id UUID NOT NULL REFERENCES projects(id),
  source_type VARCHAR(32) NOT NULL CHECK (source_type IN ('PRD_DOC', 'FIGMA_LINK', 'HTML_DOC')),
  status VARCHAR(32) NOT NULL CHECK (status IN ('PENDING', 'UPLOADED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'COMMITTED')),
  source_ref_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  generate_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  skill_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_message TEXT,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_ai_import_jobs_tenant_project_created
ON ai_import_jobs(tenant_id, project_id, created_at DESC);
```

```sql
CREATE TABLE ai_import_items (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  job_id UUID NOT NULL REFERENCES ai_import_jobs(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id),
  title VARCHAR(100) NOT NULL,
  type VARCHAR(16) NOT NULL,
  priority VARCHAR(8) NOT NULL,
  status VARCHAR(16) NOT NULL,
  feature VARCHAR(128),
  epic VARCHAR(128),
  story VARCHAR(128),
  task VARCHAR(128),
  description TEXT,
  steps_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  api_url VARCHAR(1024),
  api_method VARCHAR(16),
  tags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ai_meta_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  confidence NUMERIC(5,4),
  dedupe_key VARCHAR(256),
  selected BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_ai_import_items_job ON ai_import_items(job_id);
CREATE INDEX ix_ai_import_items_project_story ON ai_import_items(project_id, story);
```

## 5.3 新增挂载与接口目标表

```sql
CREATE TABLE api_targets (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  project_id UUID NOT NULL REFERENCES projects(id),
  name VARCHAR(255) NOT NULL,
  base_url VARCHAR(2048) NOT NULL,
  default_method VARCHAR(16),
  default_path VARCHAR(1024),
  headers_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  auth_ref_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  timeout_ms INT NOT NULL DEFAULT 10000,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  version INT NOT NULL DEFAULT 1,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_api_targets_tenant_project_name
ON api_targets(tenant_id, project_id, name);
```

```sql
CREATE TABLE testcase_bindings (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  project_id UUID NOT NULL REFERENCES projects(id),
  testcase_id UUID NOT NULL REFERENCES testcases(id) ON DELETE CASCADE,
  dataset_id UUID REFERENCES test_data_sets(id),
  api_target_id UUID REFERENCES api_targets(id),
  name VARCHAR(255) NOT NULL,
  params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  priority INT NOT NULL DEFAULT 100,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  version INT NOT NULL DEFAULT 1,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_testcase_bindings_testcase ON testcase_bindings(testcase_id);
CREATE UNIQUE INDEX uq_testcase_bindings_name
ON testcase_bindings(tenant_id, testcase_id, name);
```

## 5.4 新增报告表（修正唯一约束）

```sql
CREATE TABLE reports (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  project_id UUID NOT NULL REFERENCES projects(id),
  run_id UUID NOT NULL REFERENCES runs(id),
  report_type VARCHAR(32) NOT NULL CHECK (report_type IN ('ALLURE')),
  status VARCHAR(32) NOT NULL CHECK (status IN ('GENERATING', 'READY', 'FAILED')),
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  allure_result_key VARCHAR(1024),
  allure_report_url VARCHAR(2048),
  generated_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_reports_run_type ON reports(run_id, report_type);
CREATE INDEX ix_reports_project_created ON reports(project_id, created_at DESC);
```

---

## 6. 错误码、并发、幂等统一规则

## 6.1 错误码

- `0` 成功
- `40001` 参数错误/前置条件不满足
- `40101` 未认证
- `40301` 无权限
- `40401` 资源不存在
- `40901` 并发冲突/幂等冲突
- `42901` 限流
- `50301` 依赖不可用
- `50001` 服务内部错误

推荐 `message` 常量：

- `idempotency_key_payload_mismatch`
- `version_conflict`
- `duplicate_items_in_request`
- `binding_not_in_project`
- `api_target_not_found`
- `dataset_not_found`

## 6.2 并发

- 绑定、接口目标更新使用 `version` 乐观锁
- 批量执行 `concurrency` 允许范围 `1..100`
- 同一请求内 `(testcaseId,bindingId)` 必须唯一

## 6.3 幂等

- 适用接口：
  - `POST /api/testcases/ai-import/jobs`
  - `POST /api/api-targets`
  - `POST /api/testcases/{testcaseId}/bindings`
  - `POST /api/runs/from-testcases`
- 规则：
  - 同 key + 同 payload：返回首次结果
  - 同 key + 不同 payload：`40901`

---

## 7. 实施顺序（可执行排期）

## Phase 1（后端数据层）

1. 执行 Alembic 迁移：`testcases` 扩展 + 新建 `ai_import_jobs/items`
2. 执行 Alembic 迁移：新建 `api_targets/testcase_bindings/reports`
3. 补充索引与唯一约束

交付物：

- 迁移脚本
- ORM 模型
- Schema 定义

## Phase 2（后端接口层）

1. AI 导入任务接口 5 个
2. 挂载管理接口 8 个（api-target + binding）
3. `POST /api/runs/from-testcases`
4. `GET /api/runs/{runId}/case-runs` 可选扩展 `bindingSnapshot`

交付物：

- OpenAPI 文档
- 接口单测

## Phase 3（前端页面）

1. CasesPanel：AI导入入口 + 任务进度 + 入库提交
2. CasesTable：新增列 `feature/story/apiUrl/apiMethod` + 多选
3. 运行弹窗：`runMode=SUITE|TESTCASES`
4. ReportsPanel：报告列表与详情联动

交付物：

- 页面功能联调通过
- 埋点与异常提示

## Phase 4（联调与灰度）

1. Feature Flag：
   - `ENABLE_AI_IMPORT`
   - `ENABLE_TESTCASE_DIRECT_RUN`
2. 小流量灰度，观察失败率、重复创建率、任务耗时
3. 全量发布

---

## 8. 验收标准

- AI 导入支持 `PRD_DOC|FIGMA_LINK|HTML_DOC` 三种来源，任务链路可闭环
- `commit` 后可在用例列表看到新增字段与用例
- 用例页可完成数据集+接口挂载并保存
- 用例多选可批量执行，运行状态仍使用既有状态机
- case-runs 可追溯挂载快照
- 报告可按 run 展示并可扩展多报告类型
- 幂等与并发冲突可被稳定识别并返回统一错误码

---

## 9. 非目标（本期不做）

- 不重构现有套件执行主链路
- 不在本期引入新的运行状态枚举
- 不做跨项目数据集复用

