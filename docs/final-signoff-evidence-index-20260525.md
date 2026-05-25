# WeiTesting 最终签收证据索引（2026-05-25）

本文件只引用最终有效证据口径。若同日存在旧的 WARN 报告，以本索引列出的 `server-verification` 证据和 GitHub Run #98 为最终签收依据。

## 总结

| 项目 | 结论 | 最终证据 |
|---|---|---|
| GitHub `real-e2e` 全量门禁 | DONE | Run #98 success：<https://github.com/Inventionyin/ai-project/actions/runs/26405181929> |
| PR 收口分支 | OPEN | PR #20：<https://github.com/Inventionyin/ai-project/pull/20>，分支 `production-closure-20260525` |
| 生产域名与 HTTPS | READY | `artifacts/server-verification/production-readiness-server-20260525-101244.json` |
| Prometheus/Grafana/Jenkins 可观测入口 | READY | 同上，`summary.ready=8`，`warn=0`，`blocked=0` |
| Jenkins 备份恢复演练 | READY | `artifacts/server-verification/jenkins-restore-drill-latest.json` |
| 真实服务器性能基线趋势 | READY | `artifacts/server-verification/performance-trend-server.json` |

## Run #98 覆盖范围

Run #98 覆盖以下门禁：

- 后端 pytest。
- 前端 `npm run build`。
- generated Playwright E2E。
- production readiness dry-run。
- performance baseline dry-run。
- 外部系统诊断。
- Jira / 禅道 / Jenkins / 钉钉 smoke。
- Jira / 禅道可逆创建清理、Jenkins build trigger、钉钉回执。
- 前端真实 E2E。

## 服务器最终证据口径

`production-readiness-server-20260525-101244.json` 的最终结论：

- `conclusion=READY`
- `ready=8`
- `warn=0`
- `blocked=0`
- 前端：`https://app.evanshine.me`
- API：`https://api.evanshine.me/health`
- Grafana：`https://grafana.evanshine.me/api/health`
- Jenkins：`https://jenkins.evanshine.me/login`
- Prometheus targets：`jenkins` 与 `weitesting-backend` 均为 `up`

## 仍需业务方确认的口径

以下不属于代码/平台阻塞项，只需要业务方在验收时确认：

- 本次导入数据是否就是最终验收数据。
- P0 缺陷是否允许按当前状态放行。
- 是否需要把 Cloudflare Access 作为上线前强制项；当前口径为增强项。
