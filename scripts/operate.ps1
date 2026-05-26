param(
    [ValidateSet(
        "help",
        "start",
        "stop",
        "local-gate",
        "backend-e2e",
        "frontend-build",
        "performance",
        "production",
        "external",
        "delivery-check",
        "all-dry-run"
    )]
    [string]$Action = "help",

    [string]$ExternalTargets = "Jira",
    [switch]$WithFrontendRealE2E
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Frontend = Join-Path $Root "ai-project_front_end"

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $Root
    )

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$FilePath exited with code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
}

function Show-Help {
    Write-Host "WeiTesting operations entry point" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\scripts\operate.ps1 -Action help"
    Write-Host "  .\scripts\operate.ps1 -Action start"
    Write-Host "  .\scripts\operate.ps1 -Action local-gate"
    Write-Host "  .\scripts\operate.ps1 -Action backend-e2e"
    Write-Host "  .\scripts\operate.ps1 -Action frontend-build"
    Write-Host "  .\scripts\operate.ps1 -Action performance"
    Write-Host "  .\scripts\operate.ps1 -Action production"
    Write-Host "  .\scripts\operate.ps1 -Action external -ExternalTargets Jira,Zentao,Jenkins,DingTalk"
    Write-Host "  .\scripts\operate.ps1 -Action delivery-check"
    Write-Host "  .\scripts\operate.ps1 -Action all-dry-run"
    Write-Host ""
    Write-Host "Notes:"
    Write-Host "  local-gate runs the normal local acceptance gate."
    Write-Host "  delivery-check checks documentation evidence and runs non-invasive dry-runs."
    Write-Host "  external runs diagnostics by default; live smoke still depends on configured secrets."
}

function Test-RequiredFile {
    param([string]$RelativePath)

    $path = Join-Path $Root $RelativePath
    if (-not (Test-Path $path)) {
        throw "Missing required file: $RelativePath"
    }
    Write-Host "OK $RelativePath"
}

switch ($Action) {
    "help" {
        Show-Help
    }
    "start" {
        Invoke-Step "Start local development services" {
            Invoke-Native ".\start-dev.bat" @()
        }
    }
    "stop" {
        Invoke-Step "Stop local development services" {
            Invoke-Native ".\stop-dev.bat" @()
        }
    }
    "local-gate" {
        $args = @()
        if ($WithFrontendRealE2E) {
            $args += "-WithFrontendRealE2E"
        }
        Invoke-Step "Run local acceptance gate" {
            Invoke-Native "pwsh" (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\verify_real_e2e.ps1") + $args)
        }
    }
    "backend-e2e" {
        Invoke-Step "Run backend real database E2E only" {
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\verify_real_e2e.ps1", "-BackendE2EOnly")
        }
    }
    "frontend-build" {
        Invoke-Step "Run frontend production build" {
            Invoke-Native "npm" @("run", "build") $Frontend
        }
    }
    "performance" {
        Invoke-Step "Run performance baseline" {
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\run_performance_baseline.ps1")
        }
    }
    "production" {
        Invoke-Step "Run production readiness check" {
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\verify_production_readiness.ps1")
        }
    }
    "external" {
        Invoke-Step "Run external integration diagnostics" {
            Invoke-Native "pwsh" @(
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                ".\scripts\verify_external_integrations.ps1",
                "-Targets",
                $ExternalTargets
            )
        }
    }
    "delivery-check" {
        Invoke-Step "Check delivery evidence files" {
            Test-RequiredFile "docs\final-delivery-package-20260526.md"
            Test-RequiredFile "docs\demo-script-20260526.md"
            Test-RequiredFile "docs\operations-rerun-20260526.md"
            Test-RequiredFile "docs\post-acceptance-operations-sop.md"
            Test-RequiredFile "docs\PRODUCTION_ACCEPTANCE_CHECKLIST.md"
        }
        Invoke-Step "Run production readiness dry-run" {
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\verify_production_readiness.ps1", "-DryRun")
        }
        Invoke-Step "Run external integration diagnostics dry-run" {
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\verify_external_integrations.ps1", "-DryRun")
        }
        Invoke-Step "Run performance baseline dry-run" {
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\run_performance_baseline.ps1", "-DryRun")
        }
    }
    "all-dry-run" {
        Invoke-Step "Run all non-invasive dry-runs" {
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\verify_real_e2e.ps1", "-DryRun")
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\verify_production_readiness.ps1", "-DryRun")
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\verify_external_integrations.ps1", "-DryRun")
            Invoke-Native "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\run_performance_baseline.ps1", "-DryRun")
        }
    }
}
