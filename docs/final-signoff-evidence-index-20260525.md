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

以下口径已按当前项目阶段定版，不再作为代码/平台阻塞项：

| 事项 | 最终决策 | 放行口径 |
|---|---|---|
| 最终验收数据 | 本次导入数据作为最终验收基线 | 当前数据量、需求/用例/缺陷结构已能代表客户真实使用场景；后续新数据按增量批次进入平台 |
| P0 缺陷 | 不阻塞平台能力验收 | P0 作为业务样本和待治理风险展示，不等同于平台代码缺陷；验收看平台是否能识别、统计、治理和报告 P0 |
| Cloudflare Access | 非上线强制项 | 当前 Jenkins/Grafana/平台登录已满足内部验收；Cloudflare Access 作为外部用户开放前的安全增强项 |

## 最终签收口径

本项目按“内部试运行/验收交付”口径放行：

- 平台功能、CI/E2E、外部系统联调、生产域名 HTTPS、备份恢复、性能基线均已具备证据。
- 需求、用例、缺陷数据以当前导入批次为最终验收快照。
- 未关闭 P0 作为业务风险进入验收报告，不作为本轮平台能力交付阻塞项。
- Cloudflare Access 不进入本轮强制验收范围，后续对外开放前再补。

## 验收后运营

后续日常运行与复跑请直接按 `docs/post-acceptance-operations-sop.md` 执行。
