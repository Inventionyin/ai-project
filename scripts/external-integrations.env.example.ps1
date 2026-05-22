# Copy this file to a local, ignored file such as:
#   scripts/external-integrations.local.ps1
# Then fill values and run:
#   . .\scripts\external-integrations.local.ps1
#   .\scripts\verify_external_integrations.ps1 -DryRun
#
# Do not commit real tokens, webhook URLs, passwords, or private endpoints.

# DingTalk
$env:DINGTALK_WEBHOOK_URL = ""
$env:DINGTALK_WEBHOOK_SECRET = ""

# GitHub REST smoke outside GitHub Actions.
# GitHub Actions itself injects GITHUB_TOKEN/GITHUB_REPOSITORY automatically.
$env:WEITESTING_GITHUB_TOKEN = ""
$env:WEITESTING_GITHUB_REPOSITORY = "Inventionyin/ai-project"
$env:WEITESTING_GITHUB_WORKFLOW_FILE = ".github/workflows/real-e2e.yml"

# Jenkins
$env:JENKINS_BASE_URL = "https://jenkins.evanshine.me"
$env:JENKINS_JOB_NAME = ""
$env:JENKINS_USERNAME = ""
$env:JENKINS_API_TOKEN = ""

# Jira
$env:JIRA_BASE_URL = ""
$env:JIRA_PROJECT_KEY = ""
$env:JIRA_EMAIL = ""
$env:JIRA_TOKEN = ""
$env:JIRA_ISSUE_TYPE = ""

# Zentao
$env:ZENTAO_BASE_URL = ""
$env:ZENTAO_PRODUCT = ""
$env:ZENTAO_TOKEN = ""
$env:ZENTAO_ACCOUNT = ""
$env:ZENTAO_PASSWORD = ""
$env:ZENTAO_MODULE = ""

# Business closure marker
$env:WEITESTING_BUSINESS_CLOSURE_PREFIX = "WeiTesting Acceptance"
