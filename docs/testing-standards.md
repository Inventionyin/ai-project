# WeiTesting 测试规范

本规范定义每类变更应补哪些测试、跑哪些命令，以及 PR 中应提供哪些验证证据。

## 测试分层

### 后端单元/接口测试

- 位置：`ai-project-back-end/tests/`
- 工具：`pytest`
- 新 endpoint 至少覆盖：
  - 路由是否注册。
  - `ApiResponse` 包裹是否正确。
  - service 参数是否传入 `user/project_id`。
- 新 service 至少覆盖：
  - 权限或项目范围。
  - READY/WARN/BLOCKED 等状态映射。
  - 关键 SQL 查询顺序或查询条件。
  - 错误/缺配置时的 recommendation。

### 后端真实数据库 E2E

- 仅在需要验证真实 SQL、Alembic、事务或数据导入链路时启用。
- 本地一键门禁使用 `scripts/verify_real_e2e.ps1`，会自动创建/迁移测试库并运行后端真实库 E2E。
- 测试库连接串不得指向生产库。

### 前端构建测试

- 每次改 Vue/TypeScript/API client/router 必跑：

```powershell
cd ai-project_front_end
npm run build
```

构建失败不能合并。

### 前端 Playwright E2E

- 位置：`ai-project_front_end/tests/ui/generated/`
- 新页面、路由、关键操作必须补 Playwright 冒烟。
- route mock 尽量使用后端真实字段契约，避免只测试前端兼容字段。
- 测试断言应聚焦：
  - 页面能进入。
  - 关键状态可见。
  - 表格/指标/报告核心内容可见。
  - 关键按钮存在并可触发。

### 外部系统测试

外部系统测试分三档：

- Dry-run 配置诊断：默认 CI 可跑，不调用第三方。
- Smoke 连通性：手动启用，允许调用第三方。
- Business closure：手动启用，允许创建/触发/清理真实对象。

相关命令见 `docs/ci.md` 和 `docs/real-external-integrations.md`。

## 推荐验证命令

### 日常本地验证

```powershell
.\scripts\verify_real_e2e.ps1
```

### 只跑真实后端 E2E

```powershell
.\scripts\verify_real_e2e.ps1 -BackendE2EOnly
```

### 包含前端真实 E2E

```powershell
.\scripts\verify_real_e2e.ps1 -WithFrontendRealE2E
```

### 单独后端定向测试

```powershell
cd ai-project-back-end
$env:PYTHONPATH=(Get-Location).Path
pytest tests/test_acceptance_center_api.py -q
```

### 单独前端页面 E2E

```powershell
cd ai-project_front_end
npx playwright test tests/ui/generated/acceptance-center.spec.ts --project=chromium
```

## PR 验证说明格式

PR 中至少写：

```markdown
## Verification
- `pytest ... -q` -> N passed
- `npm run build` -> passed
- `npx playwright test ...` -> passed
```

如果某项没跑，必须写清：

- 没跑什么。
- 为什么没跑。
- 风险是什么。
- 后续由谁在什么环境补跑。

## 生成物清理

提交前不得包含：

- `ai-project_front_end/dist/`
- `ai-project_front_end/test-results/`
- `ai-project_front_end/tests/ui/reports/html/index.html`
- 临时截图、录屏、trace、下载文件。
- 本地 `.env`、密钥、私钥、公钥、Token 导出文件。

## 失败处理

- 先读失败日志，不要直接扩大超时或改断言。
- Playwright 页面空白时先确认路由、登录态、基础项目接口和 console error。
- 后端测试失败时先确认是否缺 `PYTHONPATH`、数据库服务或迁移。
- 外部 smoke 失败时先判断是配置缺失、网络不可达、凭证过期，还是业务清理失败。

## 合并门槛

必须满足：

- 与变更相关的后端测试通过。
- 前端构建通过。
- 新页面/新入口有 Playwright 冒烟。
- CI 通过，或失败项被明确判定为环境问题并有补跑计划。
- 没有生成物和密钥进入提交。
