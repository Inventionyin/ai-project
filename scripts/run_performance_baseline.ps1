[CmdletBinding()]
param(
    [switch]$Help,
    [switch]$DryRun,
    [switch]$FailOnWarn,
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$FrontendUrl = "http://127.0.0.1:4173",
    [string]$OutputPath = ".\artifacts\performance-baseline\baseline-report.json",
    [switch]$SkipBackendSmoke,
    [switch]$SkipFrontendSmoke,
    [ValidateRange(1, 1000)]
    [int]$Iterations = 10,
    [string]$BusinessPaths = "/api/ops/health/summary",
    [string]$TrendPath = ".\artifacts\performance-baseline\trend-summary.json",
    [string]$DingTalkWebhookUrl = $env:DINGTALK_WEBHOOK_URL,
    [string]$DingTalkWebhookSecret = $env:DINGTALK_WEBHOOK_SECRET
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$backendThresholdP95Ms = 1000
$frontendThresholdP95Ms = 2000

if ($Help) {
    Write-Host "Usage: .\scripts\run_performance_baseline.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -ApiBaseUrl <url> -FrontendUrl <url> -OutputPath <path>"
    Write-Host "  -SkipBackendSmoke -SkipFrontendSmoke -Iterations <1..1000>"
    Write-Host "  -BusinessPaths <comma-separated API paths> -TrendPath <path>"
    Write-Host "  -FailOnWarn (exit non-zero when conclusion is WARN or BLOCKED)"
    Write-Host "  -DryRun (print planned checks only)"
    Write-Host "  -DingTalkWebhookUrl <url> (or env DINGTALK_WEBHOOK_URL)"
    Write-Host "  -DingTalkWebhookSecret <secret> (or env DINGTALK_WEBHOOK_SECRET)"
    exit 0
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

function Send-DingTalkSummary {
    param(
        [string]$WebhookUrl,
        [string]$Secret,
        [string]$Status,
        [string]$Message
    )

    if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
        return
    }

    $WebhookUrl = Get-DingTalkSignedWebhookUrl -WebhookUrl $WebhookUrl -Secret $Secret
    $text = "[Performance Baseline][$Status] $Message`nHost: $env:COMPUTERNAME"
    if (-not [string]::IsNullOrWhiteSpace($Secret)) {
        $text += "`nDingTalk signature enabled: true"
    }

    $payload = @{
        msgtype = "text"
        text = @{
            content = $text
        }
    } | ConvertTo-Json -Depth 4

    try {
        Invoke-RestMethod -Method Post -Uri $WebhookUrl -ContentType "application/json; charset=utf-8" -Body $payload | Out-Null
        Write-Host "[Performance Baseline] DingTalk notification sent."
    }
    catch {
        Write-Warning ("[Performance Baseline] DingTalk notification failed: {0}" -f $_.Exception.Message)
    }
}

if ($DryRun) {
    Write-Host "[DryRun] Backend target: $($ApiBaseUrl.TrimEnd('/'))/health (skip=$([bool]$SkipBackendSmoke))"
    Write-Host "[DryRun] Frontend target: $FrontendUrl (skip=$([bool]$SkipFrontendSmoke))"
    Write-Host "[DryRun] Iterations: $Iterations"
    Write-Host "[DryRun] Business paths: $BusinessPaths"
    Write-Host "[DryRun] TrendPath: $TrendPath"
    Write-Host "[DryRun] OutputPath: $OutputPath"
    Write-Host "[DryRun] FailOnWarn: $([bool]$FailOnWarn)"
    exit 0
}

function Get-PercentileValue {
    param(
        [double[]]$Values,
        [double]$Percentile
    )

    if (-not $Values -or $Values.Count -eq 0) {
        return $null
    }

    $sortedValues = @($Values | Sort-Object)
    $rank = [Math]::Ceiling(($Percentile / 100.0) * $sortedValues.Count)
    $index = [Math]::Min([Math]::Max($rank - 1, 0), $sortedValues.Count - 1)
    return [Math]::Round([double]$sortedValues[$index], 2)
}

function Measure-EndpointLatency {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [int]$Count
    )

    $samples = @()
    $latencies = @()
    $errorCount = 0

    for ($i = 1; $i -le $Count; $i++) {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 10
            $stopwatch.Stop()
            $latencyMs = [Math]::Round($stopwatch.Elapsed.TotalMilliseconds, 2)
            $statusCode = [int]$response.StatusCode
            $latencies += $latencyMs
            $samples += [PSCustomObject]@{
                iteration = $i
                latencyMs = $latencyMs
                statusCode = $statusCode
                success = $true
                error = $null
            }
        }
        catch {
            $stopwatch.Stop()
            $latencyMs = [Math]::Round($stopwatch.Elapsed.TotalMilliseconds, 2)
            $errorCount++
            $samples += [PSCustomObject]@{
                iteration = $i
                latencyMs = $latencyMs
                statusCode = $null
                success = $false
                error = $_.Exception.Message
            }
        }
    }

    $maxLatency = $null
    if ($latencies.Count -gt 0) {
        $maxLatency = [Math]::Round([double](($latencies | Measure-Object -Maximum).Maximum), 2)
    }

    return [PSCustomObject]@{
        name = $Name
        url = $Url
        sampleCount = $Count
        successfulSamples = $latencies.Count
        p50Ms = Get-PercentileValue -Values $latencies -Percentile 50
        p95Ms = Get-PercentileValue -Values $latencies -Percentile 95
        maxMs = $maxLatency
        errorCount = $errorCount
        samples = $samples
        skipped = $false
    }
}

function New-SkippedResult {
    param(
        [string]$Name,
        [string]$Url
    )

    return [PSCustomObject]@{
        name = $Name
        url = $Url
        sampleCount = 0
        successfulSamples = 0
        p50Ms = $null
        p95Ms = $null
        maxMs = $null
        errorCount = 0
        samples = @()
        skipped = $true
    }
}

$backendHealthUrl = "$($ApiBaseUrl.TrimEnd('/'))/health"
$backendResult = if ($SkipBackendSmoke) {
    New-SkippedResult -Name "backend-health" -Url $backendHealthUrl
}
else {
    Measure-EndpointLatency -Name "backend-health" -Url $backendHealthUrl -Count $Iterations
}

$frontendResult = if ($SkipFrontendSmoke) {
    New-SkippedResult -Name "frontend-root" -Url $FrontendUrl
}
else {
    Measure-EndpointLatency -Name "frontend-root" -Url $FrontendUrl -Count $Iterations
}

$businessResults = @()
if (-not $SkipBackendSmoke -and -not [string]::IsNullOrWhiteSpace($BusinessPaths)) {
    foreach ($path in ($BusinessPaths -split ",")) {
        $normalizedPath = $path.Trim()
        if ([string]::IsNullOrWhiteSpace($normalizedPath)) {
            continue
        }
        if (-not $normalizedPath.StartsWith("/")) {
            $normalizedPath = "/$normalizedPath"
        }
        $businessResults += Measure-EndpointLatency -Name ("business:{0}" -f $normalizedPath) -Url "$($ApiBaseUrl.TrimEnd('/'))$normalizedPath" -Count $Iterations
    }
}

$conclusion = "READY"
if ($backendResult.skipped -and $frontendResult.skipped) {
    $conclusion = "BLOCKED"
}
elseif ((-not $backendResult.skipped -and $backendResult.successfulSamples -eq 0) -or
        (-not $frontendResult.skipped -and $frontendResult.successfulSamples -eq 0)) {
    $conclusion = "BLOCKED"
}
elseif (($backendResult.errorCount -gt 0) -or ($frontendResult.errorCount -gt 0)) {
    $conclusion = "WARN"
}
elseif (($businessResults | Where-Object { $_.errorCount -gt 0 -or $_.successfulSamples -eq 0 } | Measure-Object).Count -gt 0) {
    $conclusion = "WARN"
}
elseif ((-not $backendResult.skipped -and $backendResult.p95Ms -gt $backendThresholdP95Ms) -or
        (-not $frontendResult.skipped -and $frontendResult.p95Ms -gt $frontendThresholdP95Ms)) {
    $conclusion = "WARN"
}

$report = [PSCustomObject]@{
    generatedAt = [DateTimeOffset]::UtcNow.ToString("o")
    targets = [PSCustomObject]@{
        apiBaseUrl = $ApiBaseUrl
        backendHealthUrl = $backendHealthUrl
        frontendUrl = $FrontendUrl
        businessPaths = @($BusinessPaths -split "," | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        iterations = $Iterations
        skipBackendSmoke = [bool]$SkipBackendSmoke
        skipFrontendSmoke = [bool]$SkipFrontendSmoke
    }
    results = [PSCustomObject]@{
        backend = $backendResult
        frontend = $frontendResult
        business = $businessResults
    }
    thresholds = [PSCustomObject]@{
        backendP95Ms = $backendThresholdP95Ms
        frontendP95Ms = $frontendThresholdP95Ms
    }
    conclusion = $conclusion
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

function Update-TrendSummary {
    param(
        [string]$Path,
        [object]$Report,
        [string]$ReportPath
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }
    $trendDirectory = Split-Path -Parent $Path
    if ($trendDirectory -and -not (Test-Path -LiteralPath $trendDirectory)) {
        New-Item -ItemType Directory -Path $trendDirectory -Force | Out-Null
    }
    $history = @()
    if (Test-Path -LiteralPath $Path) {
        try {
            $existing = Get-Content -Raw -Path $Path | ConvertFrom-Json
            if ($existing.history) {
                $history = @($existing.history)
            }
        }
        catch {
            $history = @()
        }
    }
    $history += [PSCustomObject]@{
        generatedAt = $Report.generatedAt
        reportPath = $ReportPath
        conclusion = $Report.conclusion
        backendP95Ms = $Report.results.backend.p95Ms
        frontendP95Ms = $Report.results.frontend.p95Ms
        businessCount = @($Report.results.business).Count
        businessWarnCount = @($Report.results.business | Where-Object { $_.errorCount -gt 0 -or $_.successfulSamples -eq 0 }).Count
    }
    $trend = [PSCustomObject]@{
        generatedAt = [DateTimeOffset]::UtcNow.ToString("o")
        history = @($history | Select-Object -Last 100)
    }
    $trend | ConvertTo-Json -Depth 6 | Set-Content -Path $Path -Encoding UTF8
    return $trend
}

$trend = Update-TrendSummary -Path $TrendPath -Report $report -ReportPath $OutputPath
$report | Add-Member -NotePropertyName trend -NotePropertyValue ([PSCustomObject]@{ path = $TrendPath; historyCount = if ($trend) { @($trend.history).Count } else { 0 } })
$report | ConvertTo-Json -Depth 8 | Set-Content -Path $OutputPath -Encoding UTF8

Write-Host ("Performance baseline written to: {0}" -f (Resolve-Path -LiteralPath $OutputPath))
Write-Host ("Performance trend written to: {0}" -f (Resolve-Path -LiteralPath $TrendPath))
Write-Host ("Conclusion: {0}" -f $conclusion)
Send-DingTalkSummary -WebhookUrl $DingTalkWebhookUrl -Secret $DingTalkWebhookSecret -Status $conclusion -Message ("Output: {0}" -f $OutputPath)

if ($report.gate.shouldFail) {
    Write-Host "Performance baseline gate failed (FailOnWarn enabled). Conclusion=$conclusion" -ForegroundColor Red
    exit $report.gate.exitCode
}
