param(
    [switch]$Help,
    [switch]$DryRun,
    [switch]$SkipBackend,
    [switch]$SkipFrontendBuild,
    [switch]$SkipGeneratedE2E,
    [switch]$BackendE2EOnly,
    [switch]$WithFrontendRealE2E,
    [int]$GeneratedE2EWorkers = 1,
    [string]$TestDatabaseUrl = "postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_platform_e2e",
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$FrontendUrl = "http://127.0.0.1:4173",
    [string]$DingTalkWebhookUrl = $env:DINGTALK_WEBHOOK_URL,
    [string]$DingTalkWebhookSecret = $env:DINGTALK_WEBHOOK_SECRET
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "ai-project-back-end"
$frontendDir = Join-Path $root "ai-project_front_end"
$completedSteps = New-Object System.Collections.Generic.List[string]

if ($Help) {
    Write-Host "Usage: .\scripts\verify_real_e2e.ps1 [options]"
    Write-Host ""
    Write-Host "Core options:"
    Write-Host "  -SkipBackend -SkipFrontendBuild -SkipGeneratedE2E -BackendE2EOnly -WithFrontendRealE2E"
    Write-Host "  -GeneratedE2EWorkers <int> -TestDatabaseUrl <url> -ApiBaseUrl <url> -FrontendUrl <url>"
    Write-Host "  -DryRun (print planned steps only)"
    Write-Host "  -DingTalkWebhookUrl <url> (or env DINGTALK_WEBHOOK_URL)"
    Write-Host "  -DingTalkWebhookSecret <secret> (or env DINGTALK_WEBHOOK_SECRET)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\scripts\verify_real_e2e.ps1"
    Write-Host "  .\scripts\verify_real_e2e.ps1 -WithFrontendRealE2E -DryRun"
    Write-Host "  `$env:DINGTALK_WEBHOOK_URL='https://oapi.dingtalk.com/robot/send?access_token=***'; .\scripts\verify_real_e2e.ps1"
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
        [System.Collections.Generic.List[string]]$Steps,
        [string]$Message
    )

    if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
        return
    }

    $WebhookUrl = Get-DingTalkSignedWebhookUrl -WebhookUrl $WebhookUrl -Secret $Secret
    $stepText = if ($Steps.Count -gt 0) { ($Steps -join ", ") } else { "none" }
    $text = "[WeiTesting Verify][$Status] $Message`nSteps: $stepText`nHost: $env:COMPUTERNAME"
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
        Write-Host "[WeiTesting Verify] DingTalk notification sent."
    }
    catch {
        Write-Warning ("[WeiTesting Verify] DingTalk notification failed: {0}" -f $_.Exception.Message)
    }
}

function Assert-TestDatabaseUrl {
    param([string]$Url)

    $dbName = ([Uri]($Url -replace "^postgresql\+asyncpg://", "postgresql://")).AbsolutePath.TrimStart("/")
    if ([string]::IsNullOrWhiteSpace($dbName)) {
        throw "TestDatabaseUrl must include a database name."
    }
    if ($dbName.ToLowerInvariant() -notmatch "test|e2e") {
        throw "Refusing to run E2E against non-test database: $dbName"
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$Intent,
        [string[]]$CommonCauses = @(),
        [string]$NextSuggestedCommand,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "[WeiTesting Verify] $Name"
    Write-Host "============================================================"
    Push-Location $WorkingDirectory
    try {
        if ($DryRun) {
            Write-Host "[DryRun] $Intent"
            return
        }
        & $Command
        if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE"
        }
        $completedSteps.Add($Name) | Out-Null
    }
    catch {
        $errorMessage = $_.Exception.Message
        Write-Host ""
        Write-Host "---------------- FAILURE DIAGNOSTICS ----------------" -ForegroundColor Red
        Write-Host "Step name: $Name" -ForegroundColor Red
        Write-Host "Working directory: $WorkingDirectory" -ForegroundColor Red
        Write-Host "Command intent: $Intent" -ForegroundColor Red
        Write-Host "Failure: $errorMessage" -ForegroundColor Red
        if ($CommonCauses.Count -gt 0) {
            Write-Host "Common causes:" -ForegroundColor Yellow
            foreach ($cause in $CommonCauses) {
                Write-Host "  - $cause" -ForegroundColor Yellow
            }
        }
        if (-not [string]::IsNullOrWhiteSpace($NextSuggestedCommand)) {
            Write-Host "Next suggested command:" -ForegroundColor Cyan
            Write-Host "  $NextSuggestedCommand" -ForegroundColor Cyan
        }
        Write-Host "-----------------------------------------------------" -ForegroundColor Red
        throw
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $backendDir)) {
    throw "Backend directory not found: $backendDir"
}

if (-not (Test-Path $frontendDir)) {
    throw "Frontend directory not found: $frontendDir"
}

if ($BackendE2EOnly) {
    $SkipFrontendBuild = $true
    $SkipGeneratedE2E = $true
}

if (-not $SkipBackend) {
    Assert-TestDatabaseUrl $TestDatabaseUrl
    Invoke-Step "Backend E2E database setup" $backendDir "Create or migrate the PostgreSQL E2E database before backend tests." @(
        "PostgreSQL is not running or is unreachable at the TEST_DATABASE_URL host/port.",
        "Python dependencies are not installed in the current environment.",
        "Database credentials do not allow creating or migrating the E2E database."
    ) "cd `"$backendDir`"; `$env:TEST_DATABASE_URL=`"$TestDatabaseUrl`"; python scripts/setup_test_db.py" {
        $env:PYTHONPATH = "."
        $env:TEST_DATABASE_URL = $TestDatabaseUrl
        python scripts/setup_test_db.py
    }
    $backendStepName = "Backend full pytest"
    $backendPytestArgs = @("tests", "-q")
    if ($BackendE2EOnly) {
        $backendStepName = "Backend real ASGI + PostgreSQL E2E"
        $backendPytestArgs = @("tests/e2e", "-v")
    }
    $backendIntent = "Run backend pytest with PostgreSQL-backed test database."
    $backendCommonCauses = @(
        "PostgreSQL is not running or is unreachable at the TEST_DATABASE_URL host/port.",
        "The ai_test_platform_e2e database does not exist or migrations/schema are missing.",
        "Python dependencies are not installed in the current environment."
    )
    $backendSuggestedCommand = "cd `"$backendDir`"; `$env:TEST_DATABASE_URL=`"$TestDatabaseUrl`"; `$env:DATABASE_URL=`"$TestDatabaseUrl`"; pytest $($backendPytestArgs -join ' ')"
    Invoke-Step $backendStepName $backendDir $backendIntent $backendCommonCauses $backendSuggestedCommand {
        $env:PYTHONPATH = "."
        $env:TEST_DATABASE_URL = $TestDatabaseUrl
        $env:DATABASE_URL = $TestDatabaseUrl
        pytest @backendPytestArgs
    }
}

if (-not $SkipFrontendBuild) {
    Invoke-Step "Frontend production build" $frontendDir "Build the production frontend bundle with Vite and type checks." @(
        "Node dependencies are missing. Run npm ci first.",
        "TypeScript compilation errors or unresolved imports exist in frontend source.",
        "Node.js version is incompatible with the project toolchain."
    ) "cd `"$frontendDir`"; npm run build" {
        npm run build
    }
}

if (-not $SkipGeneratedE2E) {
    Invoke-Step "Frontend generated Playwright E2E" $frontendDir "Run generated Playwright UI tests for core regression coverage." @(
        "Playwright Chromium browser is not installed.",
        "Frontend dependencies are not installed or build artifacts are missing.",
        "Generated UI specs are stale or failing against recent behavior changes."
    ) "cd `"$frontendDir`"; npx playwright install --with-deps chromium; npx playwright test tests/ui/generated --reporter=line --workers=$GeneratedE2EWorkers" {
        npx playwright test tests/ui/generated --reporter=line --workers=$GeneratedE2EWorkers
    }
}

if ($WithFrontendRealE2E) {
    Invoke-Step "Frontend real Playwright E2E" $frontendDir "Run real end-to-end Playwright tests against a live backend and frontend URL." @(
        "Backend is not started or /health is unavailable.",
        "Frontend preview server is not running at the expected FrontendUrl.",
        "Environment URLs (ApiBaseUrl/FrontendUrl) do not match active services."
    ) "cd `"$frontendDir`"; npm run test:e2e:real -- --reporter=line" {
        try {
            Invoke-WebRequest -Uri "$ApiBaseUrl/health" -UseBasicParsing -TimeoutSec 5 | Out-Null
        }
        catch {
            throw "Backend health check failed at $ApiBaseUrl/health. Start FastAPI before running -WithFrontendRealE2E."
        }
        try {
            Invoke-WebRequest -Uri "$FrontendUrl" -UseBasicParsing -TimeoutSec 5 | Out-Null
        }
        catch {
            throw "Frontend readiness check failed at $FrontendUrl. Start the frontend dev/preview server before running -WithFrontendRealE2E."
        }
        $env:WEITESTING_REAL_E2E = "1"
        $env:WEITESTING_API_BASE_URL = $ApiBaseUrl
        $env:WEITESTING_FRONTEND_URL = $FrontendUrl
        $env:VITE_API_BASE_URL = $ApiBaseUrl
        npm run test:e2e:real -- --reporter=line
    }
}

Write-Host ""
Write-Host "[WeiTesting Verify] All selected checks completed."
Send-DingTalkSummary -WebhookUrl $DingTalkWebhookUrl -Secret $DingTalkWebhookSecret -Status "SUCCESS" -Steps $completedSteps -Message "All selected checks completed."
