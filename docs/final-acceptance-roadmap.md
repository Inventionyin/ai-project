# WeiTesting 最终验收推进表

更新时间：2026-05-25

这份文档用于把“已经创建过的环境/账号/配置”和“还需要真实跑完的验收动作”串起来。它不是普通说明文，而是最终交付前的执行表：每一项都要有负责人、输入、执行命令、验收证据和状态。

## 状态口径

- `DONE`：已在真实环境执行，证据已保存。
- `READY_TO_RUN`：代码、脚本和页面已具备，只等真实账号/环境变量/数据包。
- `WAITING_INPUT`：需要用户或客户提供信息。
- `BLOCKED`：环境、权限或业务限制导致暂时不能执行。
- `N/A`：本次验收不要求。

## 当前总体判断

平台主体代码已经合入 `dev`，生产验收中心、外部系统诊断脚本、生产就绪脚本、性能基线脚本、PostgreSQL/Jenkins 备份与恢复演练脚本均已具备。2026-05-25 已在真实 GitHub Actions 和 Oracle Ubuntu 生产服务器补跑最终收口检查：外部系统可逆业务闭环、生产域名 HTTPS、Prometheus/Grafana/Jenkins 可观测入口、PostgreSQL 备份可读性、Jenkins 备份恢复演练、服务器性能基线趋势均已有证据。

## 2026-05-25 生产收口证据

| 检查 | 结果 | 证据 |
|---|---|---|
| 生产就绪检查 | DONE | Oracle 服务器执行 `verify_production_readiness.sh`，`8 READY / 0 WARN / 0 BLOCKED`；本地归档：`artifacts/server-verification/production-readiness-server-20260525-101244.json` |
| PostgreSQL 备份可读性验证 | DONE | 最新备份 `/opt/weitesting/backups/postgres/weitesting-20260525T021501Z.dump.gz` 可被 `pg_restore --list` 读取，TOC Entries `597` |
| Jenkins 备份恢复演练 | DONE | 最新备份 `/opt/weitesting/backups/jenkins/jenkins-20260525-031701.tgz` 可解包，`extractedFileCount=1681`，`missingRequiredPaths=[]`；本地归档：`artifacts/server-verification/jenkins-restore-drill-latest.json` |
| 服务器性能基线趋势 | DONE | Oracle 服务器执行 `run_performance_baseline.sh`，趋势历史 `history=3`，最新结论 `READY`；本地归档：`artifacts/server-verification/performance-trend-server.json` |
| PowerShell 性能趋势脚本 | DONE | 修复第二次趋势对比读取目标快照元数据的问题，验证连续运行可写入 `trend-summary.json` |

## 2026-05-21 当前诊断结果

已执行不调用第三方的 dry-run：

| 检查 | 结果 | 说明 |
|---|---|---|
| `verify_external_integrations.ps1 -DryRun` | DONE | 本地 PowerShell 当前终端未加载第三方环境变量，因此本地 dry-run 会显示 DingTalk/Jenkins/Jira/Zentao missing；这不代表 GitHub Secrets/Variables 未配置 |
| `verify_production_readiness.ps1 -DryRun` | READY_TO_RUN | 默认检查目标为 `app/api/jenkins/grafana.evanshine.me` 和本机 Prometheus |
| `run_performance_baseline.ps1 -DryRun` | READY_TO_RUN | 默认目标为本机 `8000/4173`，真实生产基线需指定 app/api URL |

已新增本地环境变量模板：

```powershell
Copy-Item .\scripts\external-integrations.env.example.ps1 .\scripts\external-integrations.local.ps1
notepad .\scripts\external-integrations.local.ps1
. .\scripts\external-integrations.local.ps1
.\scripts\verify_external_integrations.ps1 -DryRun
```

`scripts/external-integrations.local.ps1` 已加入 `.gitignore`，用于你在本机填真实值，不会进入提交。

## 2026-05-21 GitHub Actions 真实外部系统验收记录

GitHub Actions 会从仓库 `Secrets / Variables` 注入外部系统配置，本地 PowerShell dry-run 读取不到这些值。以下记录以 GitHub Actions `real-e2e.yml` 的实际运行结果为准：

| Run | 输入 | 结果 | 证据 |
|---|---|---|---|
| `#63` | `externalSmokeTargets=Jira`，业务闭环关闭 | DONE | Jira account API reachable；Jira project `AIT` reachable |
| `#64` | `externalSmokeTargets=Jira,Zentao,Jenkins,DingTalk`，业务闭环关闭 | DONE | DingTalk webhook accepted；Jenkins job metadata reachable；Jira account/project reachable；Zentao product API reachable |
| `#65` | `externalSmokeTargets=Jira,Zentao,Jenkins,DingTalk`，业务闭环开启 | DONE | Jenkins build trigger accepted；Jira issue `AIT-11` created/deleted；Zentao bug `5` created/deleted；DingTalk webhook accepted |

对应 GitHub Actions 页面：

```text
https://github.com/Inventionyin/ai-project/actions/runs/26235196113
https://github.com/Inventionyin/ai-project/actions/runs/26235455869
https://github.com/Inventionyin/ai-project/actions/runs/26235787731
```

结论：你之前填入的 GitHub Secrets/Variables 已经被 CI 正确读取，真实外部系统 smoke 和可逆业务闭环均已通过。

## 你之前已经创建/提供过的线索

| 项 | 当前记录 | 下一步 |
|---|---|---|
| GitHub 仓库 | `Inventionyin/ai-project`，PR #18 已合入 `dev` | 继续用 GitHub Actions 跑验收工作流 |
| Jenkins | 曾部署在 Oracle Ubuntu，历史地址 `http://217.142.224.236:8080` | 确认最终是否使用域名/HTTPS，例如 `https://jenkins.<domain>` |
| 钉钉机器人 | 已创建过自定义机器人，后续建议轮换 Webhook | 将新 Webhook 放入 GitHub Secrets，不写进文档 |
| Oracle Ubuntu 服务器 | 可作为生产/验收服务器 | 确认 SSH、域名解析、备份目录和服务路径 |
| 域名 | 已有可用域名，历史文档使用 `app.evanshine.me` / `api.evanshine.me` | 确认最终域名是否沿用 |
| Jira | 已创建过 Atlassian/Jira 相关配置 | 确认 `JIRA_BASE_URL`、`JIRA_PROJECT_KEY`、`JIRA_EMAIL`、`JIRA_TOKEN` |
| 禅道 | 待确认最终产品空间/产品 ID | 确认 `ZENTAO_BASE_URL`、`ZENTAO_PRODUCT`、token 或账号密码 |
| 需求方数据 | 需求方会给一波数据 | 导入后生成最新验收报告快照 |

## 最终验收总表

| 编号 | 模块 | 状态 | 需要你/客户提供 | 我能执行的动作 | 验收证据 |
|---|---|---|---|---|---|
| A1 | 真实外部系统配置诊断 | DONE | GitHub Secrets/Variables 已配置 | GitHub Actions `real-e2e.yml` 已读取配置 | Run #63/#64/#65 |
| A2 | 真实外部系统 smoke | DONE | 外网、有效 token | GitHub Actions 已执行 smoke | DingTalk/Jira/Jenkins/Zentao smoke 输出 |
| A3 | 真实业务闭环 | DONE | 已允许创建/删除测试 issue/bug，允许触发 Jenkins job | GitHub Actions 已执行 business closure | Jira issue 创建/删除、禅道 bug 创建/删除、Jenkins build accepted、钉钉消息 |
| B1 | 域名解析 | DONE | 已沿用 `evanshine.me` 子域名 | 已核对 `app/api/jenkins/grafana` 生产入口 | 生产就绪检查全部 HTTP 200 |
| B2 | HTTPS | DONE | 服务器已提供 HTTPS 入口 | 已核对 `app/api/jenkins/grafana` HTTPS | `production-readiness-server-20260525-101244.json` |
| B3 | 访问控制 | DONE | Jenkins/Grafana 已有登录入口；Cloudflare Access 属增强项 | 已核对 Jenkins/Grafana 不作为匿名业务入口开放 | Jenkins login、Grafana health 均可达 |
| B4 | PostgreSQL 备份恢复验证 | DONE | Oracle sudo/数据库权限已可用 | 已执行备份可读性验证 | 最新 dump 可读，TOC Entries `597` |
| B5 | Jenkins 备份恢复演练 | DONE | Jenkins home/备份目录权限已可用 | 已执行 `restore_drill_jenkins.sh` | `jenkins-restore-drill-latest.json` |
| C1 | 性能基线单次报告 | DONE | 真实 app/api 地址已可用 | 已执行服务器性能基线 | 服务器 baseline JSON |
| C2 | 性能趋势 | DONE | 同一服务器环境已连续执行 | 已生成趋势历史 | `performance-trend-server.json`，`history=3` |
| D1 | 插件沙箱强隔离决策 | WAITING_INPUT | 是否要求容器/进程级强隔离 | 若要求，拆任务升级执行器 | 决策记录或升级 PR |
| D2 | 插件沙箱验收 | READY_TO_RUN | 插件样例/恶意样例范围 | 跑沙箱策略与审计测试 | 测试结果和审计记录 |
| E1 | 需求方数据导入 | WAITING_INPUT | 最终数据包和字段说明 | 导入需求、用例、缺陷数据 | 导入数量和错误报告 |
| E2 | 最新验收报告快照 | READY_TO_RUN | E1 完成后的项目数据 | 在平台生成验收报告快照 | 平台快照、Markdown 报告 |
| E3 | 最终汇报材料 | READY_TO_RUN | 最新快照和验收口径 | 生成最终验收汇报稿 | 可复制/下载的汇报稿 |

## A. 真实外部系统闭环

### 需要填入的值

Secret：

```text
DINGTALK_WEBHOOK_URL
DINGTALK_WEBHOOK_SECRET
JENKINS_API_TOKEN
JIRA_TOKEN
ZENTAO_TOKEN
```

Variable：

```text
JENKINS_BASE_URL
JENKINS_JOB_NAME
JENKINS_USERNAME
JIRA_BASE_URL
JIRA_PROJECT_KEY
JIRA_EMAIL
ZENTAO_BASE_URL
ZENTAO_PRODUCT
```

GitHub Actions 入口：

```text
https://github.com/Inventionyin/ai-project/settings/secrets/actions
```

### 执行命令

配置诊断：

```powershell
.\scripts\verify_external_integrations.ps1 -DryRun
```

Smoke：

```powershell
.\scripts\verify_external_integrations.ps1 -EnableSmoke -FailOnSmokeError
```

业务闭环：

```powershell
.\scripts\verify_external_integrations.ps1 `
  -Targets Jira,Zentao,Jenkins,DingTalk `
  -EnableSmoke `
  -EnableBusinessClosure `
  -FailOnSmokeError
```

### 验收证据

- DingTalk 群内收到测试消息。
- Jira 创建并删除测试 issue。
- 禅道创建并删除测试 bug。
- Jenkins build trigger accepted，最好能补充 build URL 或队列 URL。
- 终端输出或 CI artifact 保存。

## B. 生产域名、HTTPS、访问控制和备份演练

### 推荐域名

```text
app.<your-domain>
api.<your-domain>
jenkins.<your-domain>
grafana.<your-domain>
```

如果继续沿用现有域名，以 `docs/production-readiness.md` 中记录为准。当前脚本默认优先检查历史部署域名：`https://app.evanshine.me`、`https://api.evanshine.me`、`https://jenkins.evanshine.me`、`https://grafana.evanshine.me`。

### 生产就绪检查

PowerShell：

```powershell
.\scripts\verify_production_readiness.ps1 `
  -AppUrl https://app.example.com `
  -ApiBaseUrl https://api.example.com `
  -GrafanaUrl https://grafana.example.com `
  -JenkinsUrl https://jenkins.example.com `
  -PrometheusUrl http://127.0.0.1:9090 `
  -JenkinsBackupDir /opt/weitesting/backups/jenkins
```

Linux：

```bash
bash ./scripts/verify_production_readiness.sh \
  --app-url https://app.example.com \
  --api-base-url https://api.example.com \
  --grafana-url https://grafana.example.com \
  --jenkins-url https://jenkins.example.com \
  --prometheus-url http://127.0.0.1:9090 \
  --jenkins-backup-dir /opt/weitesting/backups/jenkins
```

### PostgreSQL 备份验证

```bash
sudo BACKUP_DIR=/opt/weitesting/backups/postgres /usr/local/bin/weitesting-backup-postgres
sudo /usr/local/bin/weitesting-verify-backup
```

### Jenkins 备份恢复演练

```bash
bash deploy/jenkins/backup_jenkins.sh
bash deploy/jenkins/restore_drill_jenkins.sh \
  --backup-dir /opt/weitesting/backups/jenkins \
  --drill-dir /opt/weitesting/restore-drills/jenkins \
  --output-path artifacts/jenkins-restore-drill/latest.json
```

## C. 性能基线和趋势

单次真实环境基线：

```powershell
.\scripts\run_performance_baseline.ps1 `
  -ApiBaseUrl https://api.example.com `
  -FrontendUrl https://app.example.com `
  -BusinessPaths "/api/ops/health/summary,/metrics" `
  -Iterations 20 `
  -OutputPath ".\artifacts\performance-baseline\baseline-$(Get-Date -Format yyyyMMdd-HHmmss).json" `
  -TrendPath ".\artifacts\performance-baseline\trend-summary.json"
```

趋势要求：

- 同一环境至少跑 3 次。
- 每次保留 baseline JSON。
- 最终保留 `trend-summary.json`。
- 若启用 `-FailOnWarn`，需要先确认阈值适合当前服务器规格。

## D. 插件沙箱强隔离

当前仓库已有插件沙箱边界文档和策略基础，详见：

```text
docs/plugin-sandbox-boundary.md
```

最终验收前先确认安全等级：

| 安全等级 | 说明 | 是否必须 |
|---|---|---|
| 策略级隔离 | 校验、审计、权限边界 | 默认需要 |
| 进程级隔离 | 插件在独立进程执行 | 需要安全增强时做 |
| 容器级隔离 | 插件在容器/沙箱环境执行 | 面向不可信第三方插件时做 |

决策口径：

- 如果插件只给内部可信团队使用，策略级隔离 + 审计可进入阶段验收。
- 如果允许第三方上传或执行不可信代码，应升级到进程级或容器级隔离。

## E. 需求方数据导入和最终验收快照

### 需要的数据

- 需求文档或需求拆解表。
- 测试用例文件。
- 缺陷清单。
- 字段说明或样例。
- 项目名称、版本、验收周期。

### 执行动作

1. 导入需求、用例、缺陷。
2. 打开平台试运行/生产验收中心。
3. 检查导入数量、风险提示、P0/P1 状态。
4. 生成最新验收报告快照。
5. 复制或下载 Markdown 报告。
6. 生成最终验收汇报稿。

### 验收证据

- 平台内数据统计截图。
- 生产验收中心截图。
- 验收报告快照 ID 或报告 Markdown。
- 最终汇报稿。

## 每次推进后的记录模板

```markdown
### 2026-05-21 执行记录

- 执行人：
- 模块：
- 命令/页面：
- 结果：DONE / WARN / BLOCKED
- 证据路径：
- 问题：
- 下一步：
```

## 最终完成定义

满足以下条件后，可以对外说“最终验收闭环已完成”：

- A1/A2/A3 均为 `DONE`，或客户书面确认某外部系统本期不纳入。
- B1/B2/B4 至少为 `DONE`；B3/B5 按客户安全要求确认。
- C1 为 `DONE`，C2 至少形成 3 次趋势记录。
- D1 有明确决策；若要求强隔离，则 D2 为 `DONE`。
- E1/E2/E3 为 `DONE`。
- `docs/PRODUCTION_ACCEPTANCE_CHECKLIST.md` 中“交付前必须确认”已逐项更新。
