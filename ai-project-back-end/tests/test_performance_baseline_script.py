from pathlib import Path


def test_performance_baseline_script_contains_required_contract():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_performance_baseline.ps1"
    content = script_path.read_text(encoding="utf-8")

    required_tokens = [
        "param(",
        "[string]$ApiBaseUrl",
        "[string]$FrontendUrl",
        "[string]$OutputPath",
        "[switch]$SkipBackendSmoke",
        "[switch]$SkipFrontendSmoke",
        "[int]$Iterations = 10",
        "Invoke-WebRequest",
        "/health",
        "p50Ms",
        "p95Ms",
        "maxMs",
        "errorCount",
        "generatedAt",
        "targets",
        "results",
        "thresholds",
        "conclusion",
        "$backendThresholdP95Ms = 1000",
        "$frontendThresholdP95Ms = 2000",
        "Get-DingTalkSignedWebhookUrl",
        "[System.Security.Cryptography.HMACSHA256]::new",
        "timestamp=",
        "sign=",
        '"READY"',
        '"WARN"',
        '"BLOCKED"',
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected script tokens: {missing}"
