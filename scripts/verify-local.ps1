param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$FullBackend,
    [switch]$IncludeE2E
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "ai-project-back-end"
$Frontend = Join-Path $Root "ai-project_front_end"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath exited with code $LASTEXITCODE"
    }
}

if (-not $SkipBackend) {
    Invoke-Step "Backend focused test suite" {
        Push-Location $Backend
        try {
            $env:PYTHONPATH = "."
            $python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
            if ($FullBackend) {
                Invoke-Native $python @("-m", "pytest", "tests", "--ignore=tests/e2e", "-q")
            } else {
                Invoke-Native $python @(
                    "-m",
                    "pytest",
                    "tests/test_auth_header_impersonation.py",
                    "tests/test_trial_operation_dashboard_api.py",
                    "tests/test_case_governance_api.py",
                    "tests/test_platform_records_api.py",
                    "-q"
                )
            }
        } finally {
            Pop-Location
        }
    }
}

if (-not $SkipFrontend) {
    Invoke-Step "Frontend typecheck and production build" {
        Push-Location $Frontend
        try {
            Invoke-Native "npm" @("run", "build")
        } finally {
            Pop-Location
        }
    }
}

if ($IncludeE2E) {
    Invoke-Step "Backend real database E2E" {
        Push-Location $Backend
        try {
            $env:PYTHONPATH = "."
            $python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
            Invoke-Native $python @("-m", "pytest", "tests/e2e", "-q")
        } finally {
            Pop-Location
        }
    }

    Invoke-Step "Frontend Playwright E2E" {
        Push-Location $Frontend
        try {
            Invoke-Native "npm" @("run", "test:e2e")
        } finally {
            Pop-Location
        }
    }
}

Write-Host ""
Write-Host "Local verification finished." -ForegroundColor Green
