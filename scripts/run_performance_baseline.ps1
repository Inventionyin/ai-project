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
    [string]$BusinessHeadersJson = $env:PERF_BASELINE_BUSINESS_HEADERS_JSON,
    [string]$BusinessAuthorization = $env:PERF_BASELINE_AUTHORIZATION,
    [string]$BusinessUserId = $env:PERF_BASELINE_USER_ID,
    [string]$BusinessTenantId = $env:PERF_BASELINE_TENANT_ID,
    [string]$BusinessRoles = $env:PERF_BASELINE_ROLES,
    [ValidateRange(1, 600000)]
    [int]$BusinessThresholdP95Ms = 2000,
    [string]$TrendPath = ".\artifacts\performance-baseline\trend-summary.json",
    [string]$DingTalkWebhookUrl = $env:DINGTALK_WEBHOOK_URL,
    [string]$DingTalkWebhookSecret = $env:DINGTALK_WEBHOOK_SECRET
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$backendThresholdP95Ms = 1000
$frontendThresholdP95Ms = 2000
$businessThresholdP95Ms = $BusinessThresholdP95Ms
$scriptVersion = "2026.05.21"

if ($Help) {
    Write-Host "Usage: .\scripts\run_performance_baseline.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -ApiBaseUrl <url> -FrontendUrl <url> -OutputPath <path>"
    Write-Host "  -SkipBackendSmoke -SkipFrontendSmoke -Iterations <1..1000>"
    Write-Host "  -BusinessPaths <comma-separated API paths> -BusinessHeadersJson <json> -TrendPath <path>"
    Write-Host "  -BusinessAuthorization <token> -BusinessUserId <uuid> -BusinessTenantId <uuid> -BusinessRoles <csv>"
    Write-Host "  -BusinessThresholdP95Ms <ms> (default: 2000)"
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

function ConvertFrom-JsonObject {
    param(
        [string]$Json,
        [string]$Name
    )

    if ([string]::IsNullOrWhiteSpace($Json)) {
        return @{}
    }

    try {
        $parsed = $Json | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "Invalid JSON for ${Name}: $($_.Exception.Message)"
    }

    $map = @{}
    foreach ($prop in $parsed.PSObject.Properties) {
        $map[$prop.Name] = [string]$prop.Value
    }
    return $map
}

function Get-BusinessRequestHeaders {
    $headers = @{}

    if (-not [string]::IsNullOrWhiteSpace($BusinessAuthorization)) {
        $authorization = $BusinessAuthorization.Trim()
        if (-not $authorization.StartsWith("Bearer ")) {
            $authorization = "Bearer $authorization"
        }
        $headers["Authorization"] = $authorization
    }

    if (-not [string]::IsNullOrWhiteSpace($BusinessUserId) -and -not [string]::IsNullOrWhiteSpace($BusinessTenantId)) {
        $headers["X-User-Id"] = $BusinessUserId.Trim()
        $headers["X-Tenant-Id"] = $BusinessTenantId.Trim()
        if (-not [string]::IsNullOrWhiteSpace($BusinessRoles)) {
            $headers["X-Roles"] = $BusinessRoles.Trim()
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($BusinessHeadersJson)) {
        $customHeaders = ConvertFrom-JsonObject -Json $BusinessHeadersJson -Name "BusinessHeadersJson"
        foreach ($entry in $customHeaders.GetEnumerator()) {
            $headers[$entry.Key] = $entry.Value
        }
    }

    return $headers
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

function Get-EndpointSummary {
    param(
        [object[]]$Samples
    )

    $allSamples = @($Samples)
    $successfulSamples = @($allSamples | Where-Object { $_.success })
    $latencies = @($successfulSamples | ForEach-Object { [double]$_.latencyMs })
    $errorSamples = @($allSamples | Where-Object { -not $_.success })
    $timeoutCount = @($errorSamples | Where-Object { $_.error -match 'timeout|timed out' }).Count

    $average = $null
    $minimum = $null
    $maximum = $null
    if ($latencies.Count -gt 0) {
        $average = [Math]::Round((($latencies | Measure-Object -Average).Average), 2)
        $minimum = [Math]::Round((($latencies | Measure-Object -Minimum).Minimum), 2)
        $maximum = [Math]::Round((($latencies | Measure-Object -Maximum).Maximum), 2)
    }

    $sampleCount = $allSamples.Count
    $successfulCount = $successfulSamples.Count
    $successRate = $null
    $errorRate = $null
    if ($sampleCount -gt 0) {
        $successRate = [Math]::Round(($successfulCount / $sampleCount) * 100, 2)
        $errorRate = [Math]::Round((($sampleCount - $successfulCount) / $sampleCount) * 100, 2)
    }

    return [PSCustomObject]@{
        sampleCount = $sampleCount
        successfulSamples = $successfulCount
        successRatePct = $successRate
        errorRatePct = $errorRate
        meanMs = $average
        minMs = $minimum
        p50Ms = Get-PercentileValue -Values $latencies -Percentile 50
        p90Ms = Get-PercentileValue -Values $latencies -Percentile 90
        p95Ms = Get-PercentileValue -Values $latencies -Percentile 95
        maxMs = $maximum
        errorCount = $errorSamples.Count
        timeoutCount = $timeoutCount
    }
}

function Get-TargetComparison {
    param(
        [object]$Current,
        [object]$Previous,
        [object]$PreviousGeneratedAt = $null,
        [object]$PreviousReportPath = $null
    )

    if (-not $Previous) {
        return [PSCustomObject]@{
            previousGeneratedAt = $null
            previousReportPath = $null
            p50DeltaMs = $null
            p90DeltaMs = $null
            p95DeltaMs = $null
            meanDeltaMs = $null
            maxDeltaMs = $null
            successRateDeltaPct = $null
            errorRateDeltaPct = $null
            errorCountDelta = $null
            timeoutCountDelta = $null
        }
    }

    return [PSCustomObject]@{
        previousGeneratedAt = $PreviousGeneratedAt
        previousReportPath = $PreviousReportPath
        p50DeltaMs = if ($Current.p50Ms -ne $null -and $Previous.p50Ms -ne $null) { [Math]::Round($Current.p50Ms - $Previous.p50Ms, 2) } else { $null }
        p90DeltaMs = if ($Current.p90Ms -ne $null -and $Previous.p90Ms -ne $null) { [Math]::Round($Current.p90Ms - $Previous.p90Ms, 2) } else { $null }
        p95DeltaMs = if ($Current.p95Ms -ne $null -and $Previous.p95Ms -ne $null) { [Math]::Round($Current.p95Ms - $Previous.p95Ms, 2) } else { $null }
        meanDeltaMs = if ($Current.meanMs -ne $null -and $Previous.meanMs -ne $null) { [Math]::Round($Current.meanMs - $Previous.meanMs, 2) } else { $null }
        maxDeltaMs = if ($Current.maxMs -ne $null -and $Previous.maxMs -ne $null) { [Math]::Round($Current.maxMs - $Previous.maxMs, 2) } else { $null }
        successRateDeltaPct = if ($Current.successRatePct -ne $null -and $Previous.successRatePct -ne $null) { [Math]::Round($Current.successRatePct - $Previous.successRatePct, 2) } else { $null }
        errorRateDeltaPct = if ($Current.errorRatePct -ne $null -and $Previous.errorRatePct -ne $null) { [Math]::Round($Current.errorRatePct - $Previous.errorRatePct, 2) } else { $null }
        errorCountDelta = if ($Current.errorCount -ne $null -and $Previous.errorCount -ne $null) { [int]$Current.errorCount - [int]$Previous.errorCount } else { $null }
        timeoutCountDelta = if ($Current.timeoutCount -ne $null -and $Previous.timeoutCount -ne $null) { [int]$Current.timeoutCount - [int]$Previous.timeoutCount } else { $null }
    }
}

function Get-TargetSnapshot {
    param(
        [object]$Result
    )

    return [PSCustomObject]@{
        name = $Result.name
        url = $Result.url
        sampleCount = $Result.sampleCount
        successfulSamples = $Result.successfulSamples
        successRatePct = $Result.successRatePct
        errorRatePct = $Result.errorRatePct
        meanMs = $Result.meanMs
        minMs = $Result.minMs
        p50Ms = $Result.p50Ms
        p90Ms = $Result.p90Ms
        p95Ms = $Result.p95Ms
        maxMs = $Result.maxMs
        errorCount = $Result.errorCount
        timeoutCount = $Result.timeoutCount
    }
}

function Write-TargetSummary {
    param(
        [string]$Label,
        [object]$Result,
        [object]$Comparison = $null
    )

    $p95 = if ($null -ne $Result.p95Ms) { "{0}ms" -f $Result.p95Ms } else { "n/a" }
    $mean = if ($null -ne $Result.meanMs) { "{0}ms" -f $Result.meanMs } else { "n/a" }
    $success = if ($null -ne $Result.successRatePct) { "{0}%" -f $Result.successRatePct } else { "n/a" }
    $delta = ""
    if ($Comparison -and $null -ne $Comparison.p95DeltaMs) {
        $delta = ", p95 {0:+0.##;-0.##;0}ms" -f $Comparison.p95DeltaMs
    }
    Write-Host ("  {0,-16} p95 {1}, mean {2}, success {3}, errors {4}{5}" -f $Label, $p95, $mean, $success, $Result.errorCount, $delta)
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
    Write-Host "[DryRun] BusinessThresholdP95Ms: $businessThresholdP95Ms"
    Write-Host "[DryRun] TrendPath: $TrendPath"
    Write-Host "[DryRun] OutputPath: $OutputPath"
    Write-Host "[DryRun] FailOnWarn: $([bool]$FailOnWarn)"
    exit 0
}

function Measure-EndpointLatency {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [int]$Count,
        [hashtable]$Headers = @{}
    )

    $samples = @()

    for ($i = 1; $i -le $Count; $i++) {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $invokeArgs = @{
                Uri = $Url
                Method = "Get"
                TimeoutSec = 10
            }
            if ($Headers.Count -gt 0) {
                $invokeArgs["Headers"] = $Headers
            }
            $response = Invoke-WebRequest @invokeArgs
            $stopwatch.Stop()
            $latencyMs = [Math]::Round($stopwatch.Elapsed.TotalMilliseconds, 2)
            $statusCode = [int]$response.StatusCode
            $samples += [PSCustomObject]@{
                iteration = $i
                latencyMs = $latencyMs
                statusCode = $statusCode
                success = $true
                error = $null
                method = "GET"
                startedAt = [DateTimeOffset]::UtcNow.ToString("o")
            }
        }
        catch {
            $stopwatch.Stop()
            $latencyMs = [Math]::Round($stopwatch.Elapsed.TotalMilliseconds, 2)
            $statusCode = $null
            if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
            $samples += [PSCustomObject]@{
                iteration = $i
                latencyMs = $latencyMs
                statusCode = $statusCode
                success = $false
                error = $_.Exception.Message
                method = "GET"
                startedAt = [DateTimeOffset]::UtcNow.ToString("o")
            }
        }
    }

    $summary = Get-EndpointSummary -Samples $samples

    return [PSCustomObject]@{
        name = $Name
        url = $Url
        sampleCount = $summary.sampleCount
        successfulSamples = $summary.successfulSamples
        successRatePct = $summary.successRatePct
        errorRatePct = $summary.errorRatePct
        meanMs = $summary.meanMs
        minMs = $summary.minMs
        p50Ms = $summary.p50Ms
        p90Ms = $summary.p90Ms
        p95Ms = $summary.p95Ms
        maxMs = $summary.maxMs
        errorCount = $summary.errorCount
        timeoutCount = $summary.timeoutCount
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
        successRatePct = $null
        errorRatePct = $null
        meanMs = $null
        minMs = $null
        p50Ms = $null
        p90Ms = $null
        p95Ms = $null
        maxMs = $null
        errorCount = 0
        timeoutCount = 0
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

$businessHeaders = Get-BusinessRequestHeaders
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
        $businessResults += Measure-EndpointLatency -Name ("business:{0}" -f $normalizedPath) -Url "$($ApiBaseUrl.TrimEnd('/'))$normalizedPath" -Count $Iterations -Headers $businessHeaders
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
elseif (($businessResults | Where-Object { $_.p95Ms -ne $null -and $_.p95Ms -gt $businessThresholdP95Ms } | Measure-Object).Count -gt 0) {
    $conclusion = "WARN"
}
elseif ((-not $backendResult.skipped -and $backendResult.p95Ms -gt $backendThresholdP95Ms) -or
        (-not $frontendResult.skipped -and $frontendResult.p95Ms -gt $frontendThresholdP95Ms)) {
    $conclusion = "WARN"
}

try {
    $gitCommit = (git rev-parse --short HEAD 2>$null)
}
catch {
    $gitCommit = $null
}

$report = [PSCustomObject]@{
    generatedAt = [DateTimeOffset]::UtcNow.ToString("o")
    metadata = [PSCustomObject]@{
        scriptVersion = $scriptVersion
        gitCommit = $gitCommit
        host = $env:COMPUTERNAME
        os = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription
        powershellVersion = $PSVersionTable.PSVersion.ToString()
    }
    targets = [PSCustomObject]@{
        apiBaseUrl = $ApiBaseUrl
        backendHealthUrl = $backendHealthUrl
        frontendUrl = $FrontendUrl
        businessPaths = @($BusinessPaths -split "," | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        businessTargets = @($businessResults | ForEach-Object { [PSCustomObject]@{ name = $_.name; url = $_.url } })
        businessHeadersConfigured = [bool]($businessHeaders.Count -gt 0)
        businessAuthMode = if ($businessHeaders.ContainsKey("Authorization")) { "authorization" } elseif ($businessHeaders.ContainsKey("X-User-Id") -and $businessHeaders.ContainsKey("X-Tenant-Id")) { "impersonation" } else { "none" }
        iterations = $Iterations
        skipBackendSmoke = [bool]$SkipBackendSmoke
        skipFrontendSmoke = [bool]$SkipFrontendSmoke
    }
    results = [PSCustomObject]@{
        backend = $backendResult
        frontend = $frontendResult
        business = $businessResults
    }
    summary = [PSCustomObject]@{
        backend = Get-TargetSnapshot -Result $backendResult
        frontend = Get-TargetSnapshot -Result $frontendResult
        business = @($businessResults | ForEach-Object { Get-TargetSnapshot -Result $_ })
    }
    thresholds = [PSCustomObject]@{
        backendP95Ms = $backendThresholdP95Ms
        frontendP95Ms = $frontendThresholdP95Ms
        businessP95Ms = $businessThresholdP95Ms
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

$report | ConvertTo-Json -Depth 12 | Set-Content -Path $OutputPath -Encoding UTF8

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
    $currentSnapshot = [PSCustomObject]@{
        generatedAt = $Report.generatedAt
        reportPath = $ReportPath
        conclusion = $Report.conclusion
        backend = Get-TargetSnapshot -Result $Report.results.backend
        frontend = Get-TargetSnapshot -Result $Report.results.frontend
        business = @($Report.results.business | ForEach-Object { Get-TargetSnapshot -Result $_ })
    }
    $previousSnapshot = if ($history.Count -gt 0) { $history[$history.Count - 1] } else { $null }

    $businessComparison = @()
    foreach ($businessItem in $currentSnapshot.business) {
        $previousBusiness = $null
        if ($previousSnapshot -and $previousSnapshot.business) {
            $previousBusiness = $previousSnapshot.business | Where-Object { $_.name -eq $businessItem.name } | Select-Object -First 1
        }
        $businessComparison += [PSCustomObject]@{
            name = $businessItem.name
            url = $businessItem.url
            p95DeltaMs = if ($previousBusiness -and $businessItem.p95Ms -ne $null -and $previousBusiness.p95Ms -ne $null) { [Math]::Round($businessItem.p95Ms - $previousBusiness.p95Ms, 2) } else { $null }
            meanDeltaMs = if ($previousBusiness -and $businessItem.meanMs -ne $null -and $previousBusiness.meanMs -ne $null) { [Math]::Round($businessItem.meanMs - $previousBusiness.meanMs, 2) } else { $null }
            errorCountDelta = if ($previousBusiness -and $businessItem.errorCount -ne $null -and $previousBusiness.errorCount -ne $null) { [int]$businessItem.errorCount - [int]$previousBusiness.errorCount } else { $null }
            successRateDeltaPct = if ($previousBusiness -and $businessItem.successRatePct -ne $null -and $previousBusiness.successRatePct -ne $null) { [Math]::Round($businessItem.successRatePct - $previousBusiness.successRatePct, 2) } else { $null }
        }
    }

    $previousGeneratedAt = if ($previousSnapshot) { $previousSnapshot.generatedAt } else { $null }
    $previousReportPath = if ($previousSnapshot) { $previousSnapshot.reportPath } else { $null }
    $comparison = [PSCustomObject]@{
        previousGeneratedAt = $previousGeneratedAt
        previousReportPath = $previousReportPath
        backend = if ($previousSnapshot) { Get-TargetComparison -Current $currentSnapshot.backend -Previous $previousSnapshot.backend -PreviousGeneratedAt $previousGeneratedAt -PreviousReportPath $previousReportPath } else { Get-TargetComparison -Current $currentSnapshot.backend -Previous $null }
        frontend = if ($previousSnapshot) { Get-TargetComparison -Current $currentSnapshot.frontend -Previous $previousSnapshot.frontend -PreviousGeneratedAt $previousGeneratedAt -PreviousReportPath $previousReportPath } else { Get-TargetComparison -Current $currentSnapshot.frontend -Previous $null }
        business = $businessComparison
        regressionCount = @($businessComparison | Where-Object { ($_.p95DeltaMs -ne $null -and $_.p95DeltaMs -gt 0) -or ($_.errorCountDelta -ne $null -and $_.errorCountDelta -gt 0) }).Count
    }

    $history += $currentSnapshot
    $trend = [PSCustomObject]@{
        generatedAt = [DateTimeOffset]::UtcNow.ToString("o")
        latest = $currentSnapshot
        comparison = $comparison
        history = @($history | Select-Object -Last 100)
    }
    $trend | ConvertTo-Json -Depth 12 | Set-Content -Path $Path -Encoding UTF8
    return $trend
}

$trend = Update-TrendSummary -Path $TrendPath -Report $report -ReportPath $OutputPath
$report | Add-Member -NotePropertyName trend -NotePropertyValue ([PSCustomObject]@{
    path = $TrendPath
    historyCount = if ($trend) { @($trend.history).Count } else { 0 }
    latest = $trend.latest
    comparison = $trend.comparison
})
$report | Add-Member -NotePropertyName comparison -NotePropertyValue $trend.comparison
$report | ConvertTo-Json -Depth 12 | Set-Content -Path $OutputPath -Encoding UTF8

Write-Host ("Performance baseline written to: {0}" -f (Resolve-Path -LiteralPath $OutputPath))
Write-Host ("Performance trend written to: {0}" -f (Resolve-Path -LiteralPath $TrendPath))
Write-Host ""
Write-Host "Performance baseline summary:"
Write-TargetSummary -Label "backend" -Result $backendResult -Comparison $trend.comparison.backend
Write-TargetSummary -Label "frontend" -Result $frontendResult -Comparison $trend.comparison.frontend
foreach ($businessResult in $businessResults) {
    $businessComparison = @($trend.comparison.business | Where-Object { $_.name -eq $businessResult.name } | Select-Object -First 1)
    Write-TargetSummary -Label $businessResult.name -Result $businessResult -Comparison $businessComparison
}
if ($trend.comparison.previousGeneratedAt) {
    Write-Host ("Trend comparison: previous run {0}, regressions {1}" -f $trend.comparison.previousGeneratedAt, $trend.comparison.regressionCount)
}
else {
    Write-Host "Trend comparison: no previous run yet"
}
Write-Host ("Conclusion: {0}" -f $conclusion)
Send-DingTalkSummary -WebhookUrl $DingTalkWebhookUrl -Secret $DingTalkWebhookSecret -Status $conclusion -Message ("Output: {0}" -f $OutputPath)

if ($report.gate.shouldFail) {
    Write-Host "Performance baseline gate failed (FailOnWarn enabled). Conclusion=$conclusion" -ForegroundColor Red
    exit $report.gate.exitCode
}
