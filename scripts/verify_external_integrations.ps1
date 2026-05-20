[CmdletBinding()]
param(
    [switch]$Help,
    [switch]$DryRun,
    [switch]$EnableSmoke,
    [switch]$FailOnSmokeError,
    [string]$Targets = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Usage {
    Write-Host "Usage: .\scripts\verify_external_integrations.ps1 [-DryRun] [-EnableSmoke] [-FailOnSmokeError] [-Targets <names>]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help      Show this help message."
    Write-Host "  -DryRun    Only check configuration, never call external APIs."
    Write-Host "  -EnableSmoke  Run minimal API smoke checks after config READY."
    Write-Host "  -FailOnSmokeError  Return non-zero when any enabled smoke check fails."
    Write-Host "  -Targets   Optional comma-separated target names: DingTalk, GitHub Actions, Jenkins, Jira, Zentao."
    Write-Host ""
    Write-Host "Environment variables:"
    Write-Host "  DINGTALK_WEBHOOK_URL, optional DINGTALK_WEBHOOK_SECRET"
    Write-Host "  WEITESTING_GITHUB_TOKEN or GITHUB_TOKEN"
    Write-Host "  WEITESTING_GITHUB_REPOSITORY or GITHUB_REPOSITORY"
    Write-Host "  WEITESTING_GITHUB_WORKFLOW_FILE or GITHUB_WORKFLOW_FILE"
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
        "DINGTALK_WEBHOOK_SECRET",
        "GITHUB_TOKEN",
        "WEITESTING_GITHUB_TOKEN",
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

function Get-EnvValue {
    param([string[]]$Names)

    foreach ($name in $Names) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value
        }
    }

    return $null
}

function Get-DingTalkSignedWebhookUrl {
    param(
        [string]$WebhookUrl,
        [string]$Secret
    )

    if ([string]::IsNullOrWhiteSpace($WebhookUrl) -or [string]::IsNullOrWhiteSpace($Secret)) {
        return $WebhookUrl
    }

    $timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $stringToSign = "$timestamp`n$Secret"
    $secretBytes = [System.Text.Encoding]::UTF8.GetBytes($Secret)
    $signBytes = [System.Text.Encoding]::UTF8.GetBytes($stringToSign)
    $hmac = [System.Security.Cryptography.HMACSHA256]::new($secretBytes)
    try {
        $signature = [Convert]::ToBase64String($hmac.ComputeHash($signBytes))
    }
    finally {
        $hmac.Dispose()
    }
    $encodedSignature = [System.Net.WebUtility]::UrlEncode($signature)
    $separator = if ($WebhookUrl.Contains("?")) { "&" } else { "?" }
    return "$WebhookUrl${separator}timestamp=$timestamp&sign=$encodedSignature"
}

function Get-IntegrationStatus {
    param(
        [string]$Name,
        [object[]]$RequiredEnvGroups
    )

    $missing = @()
    $requiredLabels = @()
    foreach ($envGroup in $RequiredEnvGroups) {
        $names = @($envGroup)
        $requiredLabels += ($names -join " or ")
        $value = Get-EnvValue -Names $names
        if ([string]::IsNullOrWhiteSpace($value)) {
            $missing += ($names -join " or ")
        }
    }

    return [PSCustomObject]@{
        Name = $Name
        Required = $requiredLabels
        Missing = $missing
        Ready = ($missing.Count -eq 0)
    }
}

function Invoke-SmokeChecks {
    param([System.Collections.Generic.List[object]]$Statuses)

    $failures = New-Object System.Collections.Generic.List[string]
    foreach ($status in $Statuses) {
        if (-not $status.Ready) {
            continue
        }
        switch ($status.Name) {
            "DingTalk" {
                try {
                    $webhook = [Environment]::GetEnvironmentVariable("DINGTALK_WEBHOOK_URL")
                    $secret = [Environment]::GetEnvironmentVariable("DINGTALK_WEBHOOK_SECRET")
                    $signedWebhook = Get-DingTalkSignedWebhookUrl -WebhookUrl $webhook -Secret $secret
                    $payload = @{
                        msgtype = "text"
                        text = @{
                            content = "WeiTesting external integration smoke"
                        }
                    } | ConvertTo-Json -Depth 4
                    Invoke-RestMethod -Method Post -Uri $signedWebhook -ContentType "application/json; charset=utf-8" -Body $payload -TimeoutSec 8 | Out-Null
                    Write-Host "[SMOKE] DingTalk webhook accepted message."
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[SMOKE] DingTalk failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "GitHub Actions" {
                try {
                    $repo = Get-EnvValue -Names @("WEITESTING_GITHUB_REPOSITORY", "GITHUB_REPOSITORY")
                    $workflow = Get-EnvValue -Names @("WEITESTING_GITHUB_WORKFLOW_FILE", "GITHUB_WORKFLOW_FILE")
                    $token = Get-EnvValue -Names @("WEITESTING_GITHUB_TOKEN", "GITHUB_TOKEN")
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
                    $failures.Add($status.Name) | Out-Null
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
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[SMOKE] Jenkins failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "Jira" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("JIRA_BASE_URL").TrimEnd("/")
                    $projectKey = [Environment]::GetEnvironmentVariable("JIRA_PROJECT_KEY")
                    $email = [Environment]::GetEnvironmentVariable("JIRA_EMAIL")
                    $token = [Environment]::GetEnvironmentVariable("JIRA_TOKEN")
                    $pair = "{0}:{1}" -f $email, $token
                    $bytes = [System.Text.Encoding]::UTF8.GetBytes($pair)
                    $basic = [System.Convert]::ToBase64String($bytes)
                    $headers = @{ Authorization = "Basic $basic" }
                    $accountUri = "$base/rest/api/3/myself"
                    Invoke-RestMethod -Method Get -Uri $accountUri -Headers $headers -TimeoutSec 10 | Out-Null
                    Write-Host "[SMOKE] Jira account API reachable."
                    $encodedProjectKey = [System.Uri]::EscapeDataString($projectKey)
                    $projectUri = "$base/rest/api/3/project/$encodedProjectKey"
                    Invoke-RestMethod -Method Get -Uri $projectUri -Headers $headers -TimeoutSec 10 | Out-Null
                    Write-Host ("[SMOKE] Jira project {0} reachable." -f $projectKey)
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
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
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[SMOKE] Zentao failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
        }
    }

    return $failures
}

function Get-TargetSet {
    param([string]$TargetNames)

    $targetSet = @{}
    if ([string]::IsNullOrWhiteSpace($TargetNames)) {
        return $targetSet
    }

    foreach ($target in ($TargetNames -split ",")) {
        $normalized = $target.Trim().ToLowerInvariant()
        if (-not [string]::IsNullOrWhiteSpace($normalized)) {
            $targetSet[$normalized] = $true
        }
    }

    return $targetSet
}

if ($Help) {
    Write-Usage
    exit 0
}

$definitions = @(
    @{ Name = "DingTalk"; Required = @("DINGTALK_WEBHOOK_URL") },
    @{ Name = "GitHub Actions"; Required = @(
        @("WEITESTING_GITHUB_TOKEN", "GITHUB_TOKEN"),
        @("WEITESTING_GITHUB_REPOSITORY", "GITHUB_REPOSITORY"),
        @("WEITESTING_GITHUB_WORKFLOW_FILE", "GITHUB_WORKFLOW_FILE")
    ) },
    @{ Name = "Jenkins"; Required = @("JENKINS_BASE_URL", "JENKINS_JOB_NAME", "JENKINS_USERNAME", "JENKINS_API_TOKEN") },
    @{ Name = "Jira"; Required = @("JIRA_BASE_URL", "JIRA_PROJECT_KEY", "JIRA_EMAIL", "JIRA_TOKEN") },
    @{ Name = "Zentao"; Required = @("ZENTAO_BASE_URL", "ZENTAO_PRODUCT", "ZENTAO_TOKEN") }
)

$targetSet = Get-TargetSet -TargetNames $Targets
if ($targetSet.Count -gt 0) {
    $definitions = @($definitions | Where-Object { $targetSet.ContainsKey($_.Name.ToLowerInvariant()) })
}

if ($definitions.Count -eq 0) {
    Write-Error "No integration definitions matched -Targets '$Targets'."
}

$statuses = New-Object System.Collections.Generic.List[object]
foreach ($definition in $definitions) {
    $statuses.Add((Get-IntegrationStatus -Name $definition.Name -RequiredEnvGroups $definition.Required))
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
    $smokeFailures = @(Invoke-SmokeChecks -Statuses $statuses)
    if ($FailOnSmokeError -and $smokeFailures.Count -gt 0) {
        Write-Error ("Smoke checks failed: {0}" -f ($smokeFailures -join ", "))
    }
}
else {
    Write-Host "[INFO] Smoke checks are disabled by default. Use -EnableSmoke to run optional API probes."
}

if ($hasMissing) {
    Write-Error "Some integrations are not ready. Fill missing environment variables and retry."
}

Write-Host "[OK] External integration configuration is READY."
