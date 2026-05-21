[CmdletBinding()]
param(
    [switch]$Help,
    [switch]$DryRun,
    [switch]$FailOnWarn,
    [string]$AppUrl = $env:WEITESTING_APP_URL,
    [string]$ApiBaseUrl = $env:WEITESTING_API_URL,
    [string]$GrafanaUrl = $env:WEITESTING_GRAFANA_URL,
    [string]$JenkinsUrl = $env:WEITESTING_JENKINS_URL,
    [string]$PrometheusUrl = $env:WEITESTING_PROMETHEUS_URL,
    [string]$JenkinsBackupDir = $env:WEITESTING_JENKINS_BACKUP_DIR,
    [string]$OutputPath = ".\artifacts\production-readiness\readiness-report.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AppUrl)) { $AppUrl = "https://app.evanshine.me" }
if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) { $ApiBaseUrl = "https://api.evanshine.me" }
if ([string]::IsNullOrWhiteSpace($GrafanaUrl)) { $GrafanaUrl = "https://grafana.evanshine.me" }
if ([string]::IsNullOrWhiteSpace($JenkinsUrl)) { $JenkinsUrl = "https://jenkins.evanshine.me" }
if ([string]::IsNullOrWhiteSpace($PrometheusUrl)) { $PrometheusUrl = "http://127.0.0.1:9090" }
if ([string]::IsNullOrWhiteSpace($JenkinsBackupDir)) { $JenkinsBackupDir = "/opt/weitesting/backups/jenkins" }

if ($Help) {
    Write-Host "Usage: .\scripts\verify_production_readiness.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -AppUrl <url> -ApiBaseUrl <url> -GrafanaUrl <url> -JenkinsUrl <url>"
    Write-Host "  -PrometheusUrl <url> -JenkinsBackupDir <path> -OutputPath <path>"
    Write-Host "  -FailOnWarn (exit non-zero when conclusion is WARN or BLOCKED)"
    Write-Host "  -DryRun (print planned checks only; no HTTP or filesystem checks)"
    exit 0
}

if ($DryRun) {
    Write-Host "[DryRun] AppUrl: $AppUrl"
    Write-Host "[DryRun] ApiBaseUrl: $ApiBaseUrl"
    Write-Host "[DryRun] GrafanaUrl: $GrafanaUrl"
    Write-Host "[DryRun] JenkinsUrl: $JenkinsUrl"
    Write-Host "[DryRun] PrometheusUrl: $PrometheusUrl"
    Write-Host "[DryRun] JenkinsBackupDir: $JenkinsBackupDir"
    Write-Host "[DryRun] OutputPath: $OutputPath"
    Write-Host "[DryRun] FailOnWarn: $([bool]$FailOnWarn)"
    exit 0
}

function New-CheckResult {
    param(
        [string]$Name,
        [string]$Status,
        [string]$Message,
        [object]$Details = $null
    )

    return [PSCustomObject]@{
        name = $Name
        status = $Status
        message = $Message
        details = $Details
    }
}

function Join-Url {
    param(
        [string]$BaseUrl,
        [string]$Path
    )

    return "{0}{1}" -f $BaseUrl.TrimEnd("/"), $Path
}

function Test-HttpEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int[]]$ExpectedStatusCodes = @(200),
        [string]$RequiredContent = ""
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15 -MaximumRedirection 0
        $statusCode = [int]$response.StatusCode
        $content = [string]$response.Content
        if ($ExpectedStatusCodes -notcontains $statusCode) {
            return New-CheckResult -Name $Name -Status "BLOCKED" -Message "Unexpected HTTP status $statusCode from $Url" -Details @{
                url = $Url
                statusCode = $statusCode
                expectedStatusCodes = $ExpectedStatusCodes
            }
        }
        if (-not [string]::IsNullOrWhiteSpace($RequiredContent) -and -not $content.Contains($RequiredContent)) {
            return New-CheckResult -Name $Name -Status "WARN" -Message "HTTP status was OK, but expected content was not found." -Details @{
                url = $Url
                statusCode = $statusCode
                requiredContent = $RequiredContent
            }
        }
        return New-CheckResult -Name $Name -Status "READY" -Message "HTTP endpoint reachable." -Details @{
            url = $Url
            statusCode = $statusCode
        }
    }
    catch {
        $statusCode = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        return New-CheckResult -Name $Name -Status "BLOCKED" -Message $_.Exception.Message -Details @{
            url = $Url
            statusCode = $statusCode
        }
    }
}

function Test-PrometheusTargets {
    param(
        [string]$BaseUrl
    )

    $targetsUrl = Join-Url -BaseUrl $BaseUrl -Path "/api/v1/targets?state=active"
    try {
        $payload = Invoke-RestMethod -Method Get -Uri $targetsUrl -TimeoutSec 15
        $activeTargets = @($payload.data.activeTargets)
        $backendTarget = $activeTargets | Where-Object { $_.labels.job -eq "weitesting-backend" } | Select-Object -First 1
        $jenkinsTarget = $activeTargets | Where-Object { $_.labels.job -eq "jenkins" } | Select-Object -First 1
        $issues = @()

        if ($null -eq $backendTarget) {
            $issues += "Prometheus target weitesting-backend is missing."
        }
        elseif ($backendTarget.health -ne "up") {
            $issues += "Prometheus target weitesting-backend is $($backendTarget.health)."
        }

        if ($null -eq $jenkinsTarget) {
            $issues += "Prometheus target jenkins is missing."
        }
        elseif ($jenkinsTarget.health -ne "up") {
            $issues += "Prometheus target jenkins is $($jenkinsTarget.health). Verify Jenkins /prometheus returns 200 and that the Jenkins Prometheus plugin/permissions are configured."
        }

        $status = if ($issues.Count -eq 0) { "READY" } else { "WARN" }
        $message = if ($issues.Count -eq 0) { "Prometheus targets are healthy." } else { $issues -join " " }
        return New-CheckResult -Name "prometheus-targets" -Status $status -Message $message -Details @{
            url = $targetsUrl
            targetCount = $activeTargets.Count
            targets = @($activeTargets | ForEach-Object {
                [PSCustomObject]@{
                    job = $_.labels.job
                    health = $_.health
                    scrapeUrl = $_.scrapeUrl
                    lastError = $_.lastError
                }
            })
        }
    }
    catch {
        return New-CheckResult -Name "prometheus-targets" -Status "WARN" -Message $_.Exception.Message -Details @{
            url = $targetsUrl
        }
    }
}

function Test-JenkinsBackup {
    param(
        [string]$BackupDir
    )

    try {
        if (-not (Test-Path -LiteralPath $BackupDir)) {
            return New-CheckResult -Name "jenkins-backup" -Status "WARN" -Message "Jenkins backup directory does not exist." -Details @{
                backupDir = $BackupDir
            }
        }

        $latestBackup = Get-ChildItem -LiteralPath $BackupDir -Filter "jenkins-*.tgz" -File -ErrorAction Stop |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object -First 1
        if ($null -eq $latestBackup) {
            return New-CheckResult -Name "jenkins-backup" -Status "WARN" -Message "No Jenkins backup archive found." -Details @{
                backupDir = $BackupDir
            }
        }

        $ageHours = [Math]::Round(([DateTime]::UtcNow - $latestBackup.LastWriteTimeUtc).TotalHours, 2)
        $status = if ($ageHours -le 36) { "READY" } else { "WARN" }
        $message = if ($status -eq "READY") { "Recent Jenkins backup archive found." } else { "Latest Jenkins backup is older than 36 hours." }
        return New-CheckResult -Name "jenkins-backup" -Status $status -Message $message -Details @{
            backupDir = $BackupDir
            latestBackup = $latestBackup.FullName
            sizeBytes = $latestBackup.Length
            ageHours = $ageHours
        }
    }
    catch {
        return New-CheckResult -Name "jenkins-backup" -Status "WARN" -Message $_.Exception.Message -Details @{
            backupDir = $BackupDir
        }
    }
}

$checks = @()
$checks += Test-HttpEndpoint -Name "app-public-url" -Url $AppUrl -ExpectedStatusCodes @(200) -RequiredContent "<div id=`"app`"></div>"
$checks += Test-HttpEndpoint -Name "api-health" -Url (Join-Url -BaseUrl $ApiBaseUrl -Path "/health") -ExpectedStatusCodes @(200) -RequiredContent '"status":"ok"'
$checks += Test-HttpEndpoint -Name "api-metrics" -Url (Join-Url -BaseUrl $ApiBaseUrl -Path "/metrics") -ExpectedStatusCodes @(200) -RequiredContent "weitesting_observability_ready"
$checks += Test-HttpEndpoint -Name "grafana-health" -Url (Join-Url -BaseUrl $GrafanaUrl -Path "/api/health") -ExpectedStatusCodes @(200) -RequiredContent '"database"'
$checks += Test-HttpEndpoint -Name "jenkins-login" -Url (Join-Url -BaseUrl $JenkinsUrl -Path "/login") -ExpectedStatusCodes @(200) -RequiredContent "Sign in to Jenkins"
$checks += Test-PrometheusTargets -BaseUrl $PrometheusUrl
$checks += Test-JenkinsBackup -BackupDir $JenkinsBackupDir

$blockedCount = @($checks | Where-Object { $_.status -eq "BLOCKED" }).Count
$warnCount = @($checks | Where-Object { $_.status -eq "WARN" }).Count
$conclusion = "READY"
if ($blockedCount -gt 0) {
    $conclusion = "BLOCKED"
}
elseif ($warnCount -gt 0) {
    $conclusion = "WARN"
}

$recommendedActions = @()
if (($checks | Where-Object { $_.name -eq "prometheus-targets" -and $_.status -ne "READY" } | Measure-Object).Count -gt 0) {
    $recommendedActions += "Repo-local /metrics is checked separately; verify Prometheus scrape config for weitesting-backend and Jenkins /prometheus only if external dashboards/alerts are required."
}
if (($checks | Where-Object { $_.name -eq "jenkins-backup" -and $_.status -ne "READY" } | Measure-Object).Count -gt 0) {
    $recommendedActions += "Run deploy/jenkins/backup_jenkins.sh and perform one restore drill before production cutover."
}
$recommendedActions += "Keep Jenkins and Grafana behind strong login or Cloudflare Access before inviting external users."
$recommendedActions += "Rotate external tokens that were shared during setup before treating this environment as production."

$report = [PSCustomObject]@{
    generatedAt = [DateTimeOffset]::UtcNow.ToString("o")
    targets = [PSCustomObject]@{
        appUrl = $AppUrl
        apiBaseUrl = $ApiBaseUrl
        grafanaUrl = $GrafanaUrl
        jenkinsUrl = $JenkinsUrl
        prometheusUrl = $PrometheusUrl
        jenkinsBackupDir = $JenkinsBackupDir
    }
    checks = $checks
    summary = [PSCustomObject]@{
        conclusion = $conclusion
        ready = @($checks | Where-Object { $_.status -eq "READY" }).Count
        warn = $warnCount
        blocked = $blockedCount
    }
    recommendedActions = $recommendedActions
    gate = [PSCustomObject]@{
        failOnWarn = [bool]$FailOnWarn
        shouldFail = [bool]($FailOnWarn -and ($conclusion -eq "WARN" -or $conclusion -eq "BLOCKED"))
        exitCode = if ($FailOnWarn -and ($conclusion -eq "WARN" -or $conclusion -eq "BLOCKED")) { 2 } else { 0 }
    }
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory -and -not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$report | ConvertTo-Json -Depth 8 | Set-Content -Path $OutputPath -Encoding UTF8

Write-Host ("Production readiness written to: {0}" -f (Resolve-Path -LiteralPath $OutputPath))
Write-Host ("Conclusion: {0}" -f $conclusion)
foreach ($check in $checks) {
    Write-Host ("[{0}] {1}: {2}" -f $check.status, $check.name, $check.message)
}

if ($report.gate.shouldFail) {
    Write-Host "Production readiness gate failed (FailOnWarn enabled)." -ForegroundColor Red
    exit $report.gate.exitCode
}
