[CmdletBinding()]
param(
    [switch]$Help,
    [switch]$DryRun,
    [switch]$EnableSmoke
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Usage {
    Write-Host "Usage: .\scripts\verify_external_integrations.ps1 [-DryRun] [-EnableSmoke]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help      Show this help message."
    Write-Host "  -DryRun    Only check configuration, never call external APIs."
    Write-Host "  -EnableSmoke  Run minimal API smoke checks after config READY."
    Write-Host ""
    Write-Host "Environment variables:"
    Write-Host "  DINGTALK_WEBHOOK_URL"
    Write-Host "  GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_WORKFLOW_FILE"
    Write-Host "  JENKINS_BASE_URL, JENKINS_JOB_NAME, JENKINS_USERNAME, JENKINS_API_TOKEN"
    Write-Host "  JIRA_BASE_URL, JIRA_PROJECT_KEY, JIRA_EMAIL, JIRA_TOKEN"
    Write-Host "  ZENTAO_BASE_URL, ZENTAO_PRODUCT, ZENTAO_TOKEN"
}

function Get-MaskedValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return "<EMPTY>"
    }
    if ($Value.Length -le 8) {
        return "****"
    }
    return ("{0}****{1}" -f $Value.Substring(0, 4), $Value.Substring($Value.Length - 2, 2))
}

function Get-RedactedMessage {
    param([string]$Message)

    $redacted = [string]$Message
    $secretEnvNames = @(
        "DINGTALK_WEBHOOK_URL",
        "GITHUB_TOKEN",
        "JENKINS_API_TOKEN",
        "JIRA_TOKEN",
        "ZENTAO_TOKEN"
    )
    foreach ($envName in $secretEnvNames) {
        $secretValue = [Environment]::GetEnvironmentVariable($envName)
        if (-not [string]::IsNullOrWhiteSpace($secretValue)) {
            $redacted = $redacted.Replace($secretValue, "***REDACTED***")
        }
    }
    $redacted = [regex]::Replace(
        $redacted,
        "(?i)(access_token|token|secret|password|api[_-]?key|authorization)=([^&\s]+)",
        '$1=***REDACTED***'
    )
    return $redacted
}

function Get-IntegrationStatus {
    param(
        [string]$Name,
        [string[]]$RequiredEnvNames
    )

    $missing = @()
    foreach ($envName in $RequiredEnvNames) {
        $value = [Environment]::GetEnvironmentVariable($envName)
        if ([string]::IsNullOrWhiteSpace($value)) {
            $missing += $envName
        }
    }

    return [PSCustomObject]@{
        Name = $Name
        Required = $RequiredEnvNames
        Missing = $missing
        Ready = ($missing.Count -eq 0)
    }
}

function Invoke-SmokeChecks {
    param([System.Collections.Generic.List[object]]$Statuses)

    foreach ($status in $Statuses) {
        if (-not $status.Ready) {
            continue
        }
        switch ($status.Name) {
            "DingTalk" {
                try {
                    $webhook = [Environment]::GetEnvironmentVariable("DINGTALK_WEBHOOK_URL")
                    Invoke-WebRequest -Uri $webhook -Method Head -TimeoutSec 8 | Out-Null
                    Write-Host "[SMOKE] DingTalk webhook reachable."
                }
                catch {
                    Write-Warning ("[SMOKE] DingTalk failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "GitHub Actions" {
                try {
                    $repo = [Environment]::GetEnvironmentVariable("GITHUB_REPOSITORY")
                    $workflow = [Environment]::GetEnvironmentVariable("GITHUB_WORKFLOW_FILE")
                    $token = [Environment]::GetEnvironmentVariable("GITHUB_TOKEN")
                    $headers = @{
                        Authorization = "Bearer $token"
                        Accept = "application/vnd.github+json"
                        "X-GitHub-Api-Version" = "2022-11-28"
                    }
                    $uri = "https://api.github.com/repos/$repo/actions/workflows/$workflow"
                    Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -TimeoutSec 10 | Out-Null
                    Write-Host "[SMOKE] GitHub workflow metadata reachable."
                }
                catch {
                    Write-Warning ("[SMOKE] GitHub Actions failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "Jenkins" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("JENKINS_BASE_URL").TrimEnd("/")
                    $job = [Environment]::GetEnvironmentVariable("JENKINS_JOB_NAME")
                    $username = [Environment]::GetEnvironmentVariable("JENKINS_USERNAME")
                    $token = [Environment]::GetEnvironmentVariable("JENKINS_API_TOKEN")
                    $pair = "{0}:{1}" -f $username, $token
                    $bytes = [System.Text.Encoding]::UTF8.GetBytes($pair)
                    $basic = [System.Convert]::ToBase64String($bytes)
                    $headers = @{ Authorization = "Basic $basic" }
                    $uri = "$base/job/$job/api/json"
                    Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -TimeoutSec 10 | Out-Null
                    Write-Host "[SMOKE] Jenkins job metadata reachable."
                }
                catch {
                    Write-Warning ("[SMOKE] Jenkins failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "Jira" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("JIRA_BASE_URL").TrimEnd("/")
                    $email = [Environment]::GetEnvironmentVariable("JIRA_EMAIL")
                    $token = [Environment]::GetEnvironmentVariable("JIRA_TOKEN")
                    $pair = "{0}:{1}" -f $email, $token
                    $bytes = [System.Text.Encoding]::UTF8.GetBytes($pair)
                    $basic = [System.Convert]::ToBase64String($bytes)
                    $headers = @{ Authorization = "Basic $basic" }
                    $uri = "$base/rest/api/3/myself"
                    Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -TimeoutSec 10 | Out-Null
                    Write-Host "[SMOKE] Jira account API reachable."
                }
                catch {
                    Write-Warning ("[SMOKE] Jira failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "Zentao" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("ZENTAO_BASE_URL").TrimEnd("/")
                    $token = [Environment]::GetEnvironmentVariable("ZENTAO_TOKEN")
                    $product = [Environment]::GetEnvironmentVariable("ZENTAO_PRODUCT")
                    $maskedToken = Get-MaskedValue -Value $token
                    $uri = "$base/api.php/v1/products/$product"
                    Invoke-RestMethod -Method Get -Uri $uri -Headers @{ token = $token } -TimeoutSec 10 | Out-Null
                    Write-Host "[SMOKE] Zentao product API reachable. token=$maskedToken"
                }
                catch {
                    Write-Warning ("[SMOKE] Zentao failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
        }
    }
}

if ($Help) {
    Write-Usage
    exit 0
}

$definitions = @(
    @{ Name = "DingTalk"; Required = @("DINGTALK_WEBHOOK_URL") },
    @{ Name = "GitHub Actions"; Required = @("GITHUB_TOKEN", "GITHUB_REPOSITORY", "GITHUB_WORKFLOW_FILE") },
    @{ Name = "Jenkins"; Required = @("JENKINS_BASE_URL", "JENKINS_JOB_NAME", "JENKINS_USERNAME", "JENKINS_API_TOKEN") },
    @{ Name = "Jira"; Required = @("JIRA_BASE_URL", "JIRA_PROJECT_KEY", "JIRA_EMAIL", "JIRA_TOKEN") },
    @{ Name = "Zentao"; Required = @("ZENTAO_BASE_URL", "ZENTAO_PRODUCT", "ZENTAO_TOKEN") }
)

$statuses = New-Object System.Collections.Generic.List[object]
foreach ($definition in $definitions) {
    $statuses.Add((Get-IntegrationStatus -Name $definition.Name -RequiredEnvNames $definition.Required))
}

$hasMissing = $false
foreach ($status in $statuses) {
    if ($status.Ready) {
        Write-Host ("[{0}] READY" -f $status.Name)
    }
    else {
        $hasMissing = $true
        Write-Host ("[{0}] MISSING" -f $status.Name)
        Write-Host ("  Missing env: {0}" -f ($status.Missing -join ", "))
    }
}

if ($DryRun) {
    Write-Host "[DryRun] Configuration validation finished. No external API calls were made."
    exit 0
}

if ($EnableSmoke) {
    Write-Host "[INFO] -EnableSmoke is on. Running minimal API smoke checks..."
    Invoke-SmokeChecks -Statuses $statuses
}
else {
    Write-Host "[INFO] Smoke checks are disabled by default. Use -EnableSmoke to run optional API probes."
}

if ($hasMissing) {
    Write-Error "Some integrations are not ready. Fill missing environment variables and retry."
}

Write-Host "[OK] External integration configuration is READY."
