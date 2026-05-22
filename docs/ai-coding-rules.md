# AI 协作开发规则

这份文档给 AI 助手、外包同学和临时接手者使用。目标是让后续开发保持同一套节奏：先读、再改、能验证、可回滚。

## 开始前

1. 先看当前分支和工作区：

```powershell
git status --short --branch
```

2. 不要回退用户已有改动。看到无关脏文件时，忽略；看到相关脏文件时，先读懂再继续。
3. 先搜索现有模式：

```powershell
rg "目标功能关键词"
rg --files
```

4. 读这些规范：

- `docs/development-standards.md`
- `docs/testing-standards.md`
- `docs/PRODUCTION_ACCEPTANCE_CHECKLIST.md`

## 修改规则

- 后端新增功能要按 endpoint/schema/service/test 成套落地。
- 前端新增页面要按 API client/view/router/sidebar/Playwright 成套落地。
- 不能只写接口不加页面入口，也不能只写页面 mock 不接真实接口。
- 不能把真实 Token、Webhook、私钥、公钥、账号密码写进仓库。
- 不能提交 Playwright report、dist、临时日志、截图等生成物。
- 不能为了让测试通过而删除断言、跳过关键测试或吞掉错误。

## 后端任务模板

新增后端能力时按这个顺序：

1. 新建或补充 `tests/test_<domain>_api.py`。
2. 让测试先失败，确认失败原因是功能缺失。
3. 新增 `app/schemas/<domain>.py`。
4. 新增或修改 `app/services/<domain>.py`。
5. 新增或修改 `app/api/v1/endpoints/<domain>.py`。
6. 在 `app/api/v1/__init__.py` 注册 router。
7. 跑定向 pytest。

## 前端任务模板

新增前端能力时按这个顺序：

1. 新增或补充 `src/lib/api/<domain>.ts`。
2. 新增或补充 `src/views/.../*.vue`。
3. 在 `src/router/index.ts` 接路由。
4. 在 `AiTestingSidebar.vue` 或对应导航入口接菜单。
5. 新增 Playwright 冒烟。
6. 跑 `npm run build` 和定向 Playwright。

## 外部系统任务模板

涉及 Jira、禅道、Jenkins、钉钉、GitHub、Webhook 时：

1. 先做配置诊断，不要求真实调用。
2. 再做 smoke 连通性，确认 token、URL、网络可达。
3. 最后做 business closure，创建/触发/清理真实对象。
4. 失败诊断必须告诉用户缺哪个字段、去哪填、下一步跑什么。
5. 已泄露或临时展示过的 token，在生产验收前必须轮换。

## 验证规则

完成后至少执行与变更匹配的命令：

```powershell
# 后端
cd ai-project-back-end
$env:PYTHONPATH=(Get-Location).Path
pytest tests/<target>.py -q

# 前端
cd ai-project_front_end
npm run build
npx playwright test tests/ui/generated/<target>.spec.ts --project=chromium
```

如果不能运行，必须在回复和 PR 中写清原因。

## 提交规则

提交前：

```powershell
git diff --check
git status --short --branch
```

提交信息使用简洁英文前缀：

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `test: ...`
- `chore: ...`

PR 描述必须包含：

- Summary
- Verification
- 未完成或需人工登录/补密钥的事项

## 给 AI 的禁止项

- 不要声称“完成”但没跑验证。
- 不要把用户给过的密钥复述到最终回答。
- 不要把外部平台登录、验证码、2FA 伪装成已完成。
- 不要把“配置存在”说成“真实业务闭环已跑通”。
- 不要把 warnings 当成无所谓；要说明是否阻塞验收。
