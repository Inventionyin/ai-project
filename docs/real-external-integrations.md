# 外部系统真实联调配置指南（保姆级）

本文用于本地/测试环境做真实外部系统联调前的准备。
目标：用一条脚本先检查配置是否齐全，再按需做可选 smoke 验证。
注意：**所有 token 只放环境变量，不要写入代码仓库。**

## 1. 一键验证脚本

脚本路径：`scripts/verify_external_integrations.ps1`

常用命令：

```powershell
# 只做配置检查（推荐先跑）
.\scripts\verify_external_integrations.ps1 -DryRun

# 查看帮助
.\scripts\verify_external_integrations.ps1 -Help

# 配置通过后，做可选 API smoke（会访问外网）
.\scripts\verify_external_integrations.ps1 -EnableSmoke
```

行为说明：

1. `-DryRun`：只输出每个系统 `READY/MISSING`，并列出缺失变量，不会访问外部网络。
2. 默认不做 API 调用；只有加 `-EnableSmoke` 才会做最小探测。
3. token 不会持久化到 repo，日志只输出脱敏信息。

---

## 2. 需要的环境变量总览

必须配置以下变量（至少保证你要联调的系统对应变量完整）：

1. DingTalk
   `DINGTALK_WEBHOOK_URL`
2. GitHub Actions
   `GITHUB_TOKEN`
   `GITHUB_REPOSITORY`（格式：`owner/repo`）
   `GITHUB_WORKFLOW_FILE`（例如：`.github/workflows/ci.yml`）
3. Jenkins
   `JENKINS_BASE_URL`
   `JENKINS_JOB_NAME`
   `JENKINS_USERNAME`
   `JENKINS_API_TOKEN`
4. Jira
   `JIRA_BASE_URL`
   `JIRA_PROJECT_KEY`
   `JIRA_EMAIL`
   `JIRA_TOKEN`
5. 禅道（Zentao）
   `ZENTAO_BASE_URL`
   `ZENTAO_PRODUCT`
   `ZENTAO_TOKEN`

---

## 3. 去哪里拿值 + 填哪里

以下示例均为 PowerShell 临时设置（仅当前终端会话有效）：

```powershell
$env:VAR_NAME = "your-value"
```

### 3.1 DingTalk（机器人 Webhook）

去哪里拿：

1. 进入目标钉钉群。
2. 群设置 -> 智能群助手/机器人 -> 添加自定义机器人。
3. 配置安全策略后，复制 Webhook URL。

填哪里：

```powershell
$env:DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=***"
```

---

### 3.2 GitHub Actions

去哪里拿：

1. `GITHUB_TOKEN`：GitHub -> 右上角头像 -> Settings -> Developer settings -> Personal access tokens。
   建议最小权限：`repo`、`workflow`（按你的仓库策略微调）。
2. `GITHUB_REPOSITORY`：你的仓库路径，例如 `acme/ai-project`。
3. `GITHUB_WORKFLOW_FILE`：仓库里 workflow 文件相对路径，如 `.github/workflows/ci.yml`。

填哪里：

```powershell
$env:GITHUB_TOKEN = "ghp_xxx"
$env:GITHUB_REPOSITORY = "owner/repo"
$env:GITHUB_WORKFLOW_FILE = ".github/workflows/ci.yml"
```

---

### 3.3 Jenkins

去哪里拿：

1. `JENKINS_BASE_URL`：Jenkins 访问地址，例如 `https://jenkins.company.com`。
2. `JENKINS_JOB_NAME`：Job 名称（与 Jenkins 页面一致）。
3. `JENKINS_USERNAME`：你的 Jenkins 用户名。
4. `JENKINS_API_TOKEN`：Jenkins -> 用户设置 -> API Token -> 生成 token。

填哪里：

```powershell
$env:JENKINS_BASE_URL = "https://jenkins.company.com"
$env:JENKINS_JOB_NAME = "backend-ci"
$env:JENKINS_USERNAME = "alice"
$env:JENKINS_API_TOKEN = "your-jenkins-token"
```

---

### 3.4 Jira

去哪里拿：

1. `JIRA_BASE_URL`：例如 `https://your-org.atlassian.net`。
2. `JIRA_PROJECT_KEY`：项目 key（项目页面可见，例如 `AIT`）。
3. `JIRA_EMAIL`：你的 Atlassian 登录邮箱。
4. `JIRA_TOKEN`：Atlassian Account -> Security -> API token -> Create API token。

填哪里：

```powershell
$env:JIRA_BASE_URL = "https://your-org.atlassian.net"
$env:JIRA_PROJECT_KEY = "AIT"
$env:JIRA_EMAIL = "you@company.com"
$env:JIRA_TOKEN = "your-jira-api-token"
```

---

### 3.5 禅道（Zentao）

去哪里拿：

1. `ZENTAO_BASE_URL`：禅道服务地址。
2. `ZENTAO_PRODUCT`：产品 ID（通常在产品页面 URL 或 API 文档里可见）。
3. `ZENTAO_TOKEN`：禅道 API token（在账号/API 配置页生成）。

填哪里：

```powershell
$env:ZENTAO_BASE_URL = "https://zentao.company.com"
$env:ZENTAO_PRODUCT = "1"
$env:ZENTAO_TOKEN = "your-zentao-token"
```

---

## 4. 推荐执行顺序

1. 先配置你本次联调需要的环境变量。
2. 跑 dry run：

```powershell
.\scripts\verify_external_integrations.ps1 -DryRun
```

3. 如果输出有 `MISSING`，按提示补齐变量后重跑 dry run。
4. 全部 `READY` 后，可选跑 smoke：

```powershell
.\scripts\verify_external_integrations.ps1 -EnableSmoke
```

---

## 5. 失败怎么看

常见输出与处理：

1. `[XXX] MISSING`
   说明变量没设置或为空。按脚本列出的 `Missing env` 补齐即可。
2. `Some integrations are not ready`
   说明至少一个系统配置不完整。先跑 `-DryRun` 查缺失项。
3. `[SMOKE] ... failed`
   配置可能完整但网络/权限/地址有问题，重点检查：
   - Base URL 是否可达（公司内网/VPN）
   - Token 是否过期
   - 账号是否有目标资源权限（仓库、Job、项目、产品）

---

## 6. 安全注意事项

1. 不要把 token 写入脚本、`*.env` 模板、README 示例中的真实值。
2. 不要提交含真实 token 的终端历史截图。
3. 联调完成后，关闭终端或清理环境变量会话，避免共享机器泄露。
