# WeiTesting Agent Guide

本文件是本仓库的 AI / agent / 临时接手者入口。进入仓库后先读本文件，再读关联规范。目标是让每次改动都能成套落地、可验证、可回滚，并避免把功能做散。

## 事实源

- 开发规范：`docs/development-standards.md`
- AI 协作规则：`docs/ai-coding-rules.md`
- 测试规范：`docs/testing-standards.md`
- 生产验收清单：`docs/PRODUCTION_ACCEPTANCE_CHECKLIST.md`
- 外部系统联调：`docs/real-external-integrations.md`
- Token 治理：`docs/token-governance.md`
- 插件沙箱边界：`docs/plugin-sandbox-boundary.md`
- 性能基线：`docs/performance-baseline.md`

当文档、代码和运行结果冲突时，优先级为：当前运行行为 > 接口响应和日志 > 测试结果 > 当前代码 > 文档说明 > 历史聊天记录。

## 开始前

1. 查看分支和脏文件：

```powershell
git status --short --branch
```

2. 不要回滚用户或其他 agent 已经产生的改动。无关脏文件忽略；相关脏文件先读懂再改。
3. 先用 `rg` / `rg --files` 搜索现有实现，复用本仓库已有 endpoint、service、schema、API client、页面壳层和测试模式。
4. 新需求先判断属于哪个产品区域：仪表盘、资产中心、AI 能力、自动化执行、设置、验收/运维。

## 产品信息架构

后续页面和导航按以下结构收敛，避免把建设能力、资产、执行、配置混在一起：

- 仪表盘：项目概览、可视化、自定义看板、最新验收快照。
- 资产中心：需求管理、用例管理、接口管理、测试套件。
- AI 能力：需求解析、自动生成测试用例、用例治理、变更影响分析。
- 自动化执行：UI 自动化、接口自动化、性能自动化、运行记录、报告中心。
- 设置：权限、环境配置、集成配置、API Token / CI Token、插件市场、安全审计、运维健康。

普通用户优先看到业务工作入口；管理员配置、运维、Token、插件等能力放在设置或二级页面中。

## 成套落地规则

用户可见能力不能只落一半：

- 后端能力要包含 endpoint、schema、service、权限/租户隔离、测试。
- 前端能力要包含 API client、view、router、sidebar、loading/error/empty/refresh 状态、Playwright 冒烟。
- 配置类能力要包含字段校验、失败诊断、缺失项说明和下一步操作。
- 报告/验收类能力要包含可复制口径、可下载报告、状态来源和阻塞原因。
- 外部系统能力要区分配置诊断、连通性 smoke、真实业务闭环，不能把“配置存在”说成“闭环完成”。

## 接口与契约

- 新接口放在 `ai-project-back-end/app/api/v1/endpoints/`，并注册到 `app/api/v1/__init__.py`。
- 项目内资源路径使用 `/api/projects/{projectId}/...`。
- 统一使用 `ApiResponse[T]` 响应包裹。
- endpoint 只做依赖注入、参数校验、调用 service 和事务收口。
- service 负责业务判断、项目存在性、权限、tenant_id / project_id 过滤。
- 对外响应不得包含 token、secret、password、apiKey、webhook 明文。
- 聚合接口返回 `READY` / `WARN` / `BLOCKED` 时必须给出原因和建议。

## 前端边界

- API client 放在 `ai-project_front_end/src/lib/api/`，优先使用 `requestJson` 和 `authHeader`。
- 项目内页面统一通过 `createProjectShellPage` 进入 `AiTestingPlatformShell`。
- 导航入口主要维护在 `ai-project_front_end/src/components/figma/ai-testing-platform/AiTestingSidebar.vue`。
- 页面要服务真实工作流，不做营销式 hero，不堆说明文字。
- 指标不要重复堆放：验收页看结论，资产页看资产，用例治理页看治理问题，仪表盘看组合态势。

## 验证与证据

改完后运行与变更匹配的验证，并在最终回复或 PR 中说明结果。

后端示例：

```powershell
cd ai-project-back-end
$env:PYTHONPATH=(Get-Location).Path
pytest tests/<target>.py -q
```

前端示例：

```powershell
cd ai-project_front_end
npm run build
npx playwright test tests/ui/generated/<target>.spec.ts --project=chromium
```

如果本地数据库、Docker、外部平台登录、验证码、2FA 或密钥缺失导致无法验证，要明确写出阻塞原因和下一步。

## 禁止项

- 不提交明文密钥、Webhook、Token、私钥、公钥、账号密码。
- 不提交 `dist/`、Playwright report、临时截图、日志、缓存等生成物。
- 不为了通过测试而删除断言、跳过关键测试或吞掉错误。
- 不用历史聊天记录覆盖当前代码和运行事实。
- 不把外部平台需要人工登录/授权的动作伪装成已经完成。
- 不把一次性脚本、临时字段或硬编码项目 ID 扩散到正式代码。

## 完成标准

一次开发任务完成时，应满足：

- 入口清晰：用户能从导航或页面找到功能。
- 契约清晰：接口路径、请求、响应和状态语义可追踪。
- 失败可诊断：错误信息能说明缺什么、哪里失败、下一步做什么。
- 权限可控：管理员和普通用户看到的入口符合职责。
- 证据可复现：有测试、脚本、截图、日志或报告证明关键路径跑过。
- 变更可回滚：改动范围聚焦，没有混入无关重构和生成物。
