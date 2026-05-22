param(
    [string]$AppUrl = "https://app.evanshine.me",
    [string]$ApiUrl = "https://api.evanshine.me",
    [string]$ProjectId = "ad87792d-c392-4557-a181-d90f14ff2a2f"
)

$ErrorActionPreference = "Stop"

function Invoke-JsonGet {
    param([string]$Url)

    Write-Host "GET $Url" -ForegroundColor Cyan
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 20
        Write-Host "HTTP $($response.StatusCode)" -ForegroundColor Green
        return $response.Content
    } catch {
        Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

$health = Invoke-JsonGet "$ApiUrl/health"
if ($health -notmatch '"status"\s*:\s*"ok"') {
    throw "API health check did not return status ok: $health"
}

$app = Invoke-WebRequest -Uri $AppUrl -UseBasicParsing -TimeoutSec 20
if ($app.StatusCode -ne 200) {
    throw "App page did not return HTTP 200"
}
Write-Host "App page HTTP $($app.StatusCode)" -ForegroundColor Green

Write-Host ""
Write-Host "Authenticated checks require a browser login token. Run the Playwright/manual smoke for:" -ForegroundColor Yellow
Write-Host "$AppUrl/projects/$ProjectId/trial-operation"

Write-Host ""
Write-Host "Production public checks finished." -ForegroundColor Green
