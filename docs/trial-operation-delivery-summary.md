# WeiTesting 试运行交付说明

更新时间：2026-05-22

## 当前结论

项目已具备本地演示和试运行验收汇报条件。平台已完成真实数据导入、用例库治理、AI 治理建议、确认应用、执行结果接入、完成度展示、验收报告和报告快照闭环。

当前本地验证结果：

- 后端健康检查：`/health` 返回 `ok`
- 后端关键回归：`28 passed`
- 前端生产构建：`npm run build` 通过

## 已完成能力

- 真实需求、测试资产、缺陷数据导入。
- 需求、用例、缺陷、风险提示、缺陷聚类的试运行可视化。
- 正式用例、测试点、平台补号的分层统计。
- 重复标题、低价值候选、P0 覆盖密度治理视图。
- AI/规则混合治理建议生成。
- 治理建议勾选确认后应用，应用动作写入审计日志。
- 治理历史展示，包含生成批次、应用建议数、更新用例数。
- 执行结果接入，写入 `Run` / `CaseRun` 后看板自动更新 `executedCaseRuns`。
- 试运行完成度展示。
- 验收报告生成、复制、下载。
- 验收报告快照保存、历史查看、复制、下载。
- 验收汇报稿自动生成，包含完成度、治理历史和交付留痕。
- LongCat OpenAI-compatible LLM 本地配置覆盖。

## 本地启动入口

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- 登录账号：`qa@example.com`

密码使用本地环境配置或种子用户初始化密码。

## 推荐演示流程

1. 进入项目试运行看板。
2. 查看顶部试运行完成度。
3. 在“用例库治理”查看正式用例、测试点、平台补号、重复标题、低价值候选和 P0 密度。
4. 点击“生成治理建议”。
5. 勾选建议并点击“确认应用”。
6. 查看治理历史。
7. 在“执行结果接入”写入一轮核心用例执行结果。
8. 点击“生成报告”。
9. 点击“保存快照”。
10. 复制或下载“验收汇报稿”。

## 一键验证

本地 focused 验证：

```powershell
.\scripts\verify-local.ps1
```

完整后端验证：

```powershell
.\scripts\verify-local.ps1 -FullBackend
```

包含真实数据库和前端 E2E：

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

## 生产项状态

仓库已具备生产检查和备份脚本：

- `scripts/check-production.ps1`
- `scripts/verify_production_readiness.ps1`
- `scripts/backup-production-postgres.sh`
- `scripts/verify-production-backup.sh`
- `deploy/nginx/weitesting.conf.template`
- `deploy/observability/*`
- `deploy/jenkins/backup_jenkins.sh`
- `deploy/jenkins/restore_drill_jenkins.sh`

已完成公开生产检查：

- `https://api.evanshine.me/health` 返回 HTTP 200，健康状态为 `ok`。
- `https://app.evanshine.me` 返回 HTTP 200。

这些脚本可以直接用于最终环境检查，但以下动作必须依赖真实生产环境权限或业务方确认。

## 仍需外部信息

- 最终生产域名：前端、API、Jenkins、Grafana。
- 服务器登录权限或 CI/CD 部署权限。
- HTTPS 证书或 Cloudflare/DNS 管理权限。
- 生产数据库连接方式和备份目录。
- Jenkins 生产访问控制策略和备份目录。
- 业务方对 P0 缺陷的最终状态确认。
- 是否需要把当前 `dev` 分支推送到 `fork` 并创建 Pull Request。

## 当前验收口径

平台功能闭环已完成；最终业务验收仍应以真实生产环境、真实执行结果、P0 缺陷关闭状态和最新报告快照为准。
