from pathlib import Path


def test_performance_baseline_script_contains_required_contract():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_performance_baseline.ps1"
    content = script_path.read_text(encoding="utf-8")

    required_tokens = [
        "param(",
        "[switch]$FailOnWarn",
        "[string]$ApiBaseUrl",
        "[string]$FrontendUrl",
        "[string]$OutputPath",
        "[switch]$SkipBackendSmoke",
        "[switch]$SkipFrontendSmoke",
        "[int]$Iterations = 10",
        "[string]$BusinessPaths",
        "[string]$BusinessHeadersJson",
        "[string]$BusinessAuthorization",
        "[string]$BusinessUserId",
        "[string]$BusinessTenantId",
        "[string]$BusinessRoles",
        "PERF_BASELINE_BUSINESS_HEADERS_JSON",
        "PERF_BASELINE_AUTHORIZATION",
        "PERF_BASELINE_USER_ID",
        "PERF_BASELINE_TENANT_ID",
        "Get-BusinessRequestHeaders",
        "[string]$TrendPath",
        "Invoke-WebRequest",
        "/health",
        "meanMs",
        "minMs",
        "p50Ms",
        "p90Ms",
        "p95Ms",
        "maxMs",
        "errorCount",
        "timeoutCount",
        "successRatePct",
        "errorRatePct",
        "generatedAt",
        "targets",
        "businessTargets",
        "businessAuthMode",
        "results",
        "summary",
        "business",
        "trend",
        "latest",
        "comparison",
        "regressionCount",
        "p95DeltaMs",
        "errorCountDelta",
        "thresholds",
        "conclusion",
        "gate",
        "failOnWarn",
        "shouldFail",
        "exitCode",
        "$backendThresholdP95Ms = 1000",
        "$frontendThresholdP95Ms = 2000",
        "$businessThresholdP95Ms = $BusinessThresholdP95Ms",
        "[int]$BusinessThresholdP95Ms = 2000",
        "metadata",
        "gitCommit",
        "scriptVersion",
        "COMPUTERNAME",
        "Get-DingTalkSignedWebhookUrl",
        "[System.Security.Cryptography.HMACSHA256]::new",
        "timestamp=",
        "sign=",
        '"READY"',
        '"WARN"',
        '"BLOCKED"',
        "Performance baseline summary:",
        "Trend comparison:",
        "Performance baseline gate failed (FailOnWarn enabled).",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected script tokens: {missing}"


def test_bash_performance_baseline_script_matches_operator_contract():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_performance_baseline.sh"
    content = script_path.read_text(encoding="utf-8")

    required_tokens = [
        "SKIP_BACKEND_SMOKE=0",
        "SKIP_FRONTEND_SMOKE=0",
        "BUSINESS_THRESHOLD_P95_MS=2000",
        "DINGTALK_WEBHOOK_URL",
        "DINGTALK_WEBHOOK_SECRET",
        "--skip-backend-smoke",
        "--skip-frontend-smoke",
        "--business-threshold-p95-ms",
        "skipBackendSmoke",
        "skipFrontendSmoke",
        "skipped_result",
        "send_dingtalk",
        "sign_dingtalk_url",
        "metadata",
        "gitCommit",
        "scriptVersion",
        "socket.gethostname",
        '"businessP95Ms"',
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected bash script tokens: {missing}"
