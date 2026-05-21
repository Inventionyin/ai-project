# WeiTesting 最终验收推进表

更新时间：2026-05-21

这份文档用于把“已经创建过的环境/账号/配置”和“还需要真实跑完的验收动作”串起来。它不是普通说明文，而是最终交付前的执行表：每一项都要有负责人、输入、执行命令、验收证据和状态。

## 状态口径

- `DONE`：已在真实环境执行，证据已保存。
- `READY_TO_RUN`：代码、脚本和页面已具备，只等真实账号/环境变量/数据包。
- `WAITING_INPUT`：需要用户或客户提供信息。
- `BLOCKED`：环境、权限或业务限制导致暂时不能执行。
- `N/A`：本次验收不要求。

## 当前总体判断

平台主体代码已经合入 `dev`，生产验收中心、外部系统诊断脚本、生产就绪脚本、性能基线脚本、PostgreSQL/Jenkins 备份与恢复演练脚本均已具备。接下来要做的是在你的真实环境里逐项执行，并把输出报告、截图、URL 或平台快照作为证据归档。

## 2026-05-21 当前诊断结果

已执行不调用第三方的 dry-run：

| 检查 | 结果 | 说明 |
|---|---|---|
| `verify_external_integrations.ps1 -DryRun` | WAITING_INPUT | DingTalk、GitHub Actions、本地 Jenkins、Jira、Zentao 环境变量均未在当前终端设置 |
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
| A1 | 真实外部系统配置诊断 | READY_TO_RUN | GitHub Secrets/Variables 或本地 env | 跑 `verify_external_integrations.ps1 -DryRun` | dry-run 全部 READY 输出 |
| A2 | 真实外部系统 smoke | READY_TO_RUN | 外网/VPN、有效 token | 跑 `verify_external_integrations.ps1 -EnableSmoke -FailOnSmokeError` | DingTalk/Jira/Jenkins/Zentao smoke 输出 |
| A3 | 真实业务闭环 | READY_TO_RUN | 允许创建/删除测试 issue/bug，允许触发 Jenkins job | 跑 `verify_external_integrations.ps1 -EnableSmoke -EnableBusinessClosure -FailOnSmokeError` | Jira issue 创建/删除、禅道 bug 创建/删除、Jenkins build accepted、钉钉消息 |
| B1 | 域名解析 | WAITING_INPUT | DNS 控制台权限或截图确认 | 配置/核对 `app/api/jenkins/grafana` A/CNAME | DNS 生效截图或 `nslookup` 输出 |
| B2 | HTTPS | WAITING_INPUT | 服务器 sudo 权限、最终域名 | 配置 Nginx/certbot | `https://...` 访问成功 |
| B3 | 访问控制 | WAITING_INPUT | 是否使用 Cloudflare/强登录策略 | 配置 Jenkins/Grafana 访问限制 | 匿名访问被拒，授权用户可进 |
| B4 | PostgreSQL 备份恢复验证 | READY_TO_RUN | 服务器 sudo/数据库权限 | 跑备份和 `verify-production-backup.sh` | 备份文件路径和 restore list 输出 |
| B5 | Jenkins 备份恢复演练 | READY_TO_RUN | Jenkins home/备份目录权限 | 跑 `backup_jenkins.sh` 和 `restore_drill_jenkins.sh` | `latest.json` 或终端输出 |
| C1 | 性能基线单次报告 | READY_TO_RUN | 真实 app/api 地址 | 跑 `run_performance_baseline` | baseline JSON |
| C2 | 性能趋势 | READY_TO_RUN | 同一环境多次执行窗口 | 连续跑 3 次以上 baseline | trend-summary JSON |
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
