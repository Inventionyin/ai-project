from pathlib import Path


def test_verify_real_e2e_script_dry_run_path_avoids_outbound_notification_call():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "verify_real_e2e.ps1"
    content = script_path.read_text(encoding="utf-8")

    required_tokens = [
        "[switch]$DryRun",
        "if ($DryRun) {",
        "Write-Host \"[DryRun] $Intent\"",
        "return",
        "Get-DingTalkSignedWebhookUrl",
        "[System.Security.Cryptography.HMACSHA256]::new",
        "timestamp=",
        "sign=",
        "Invoke-RestMethod -Method Post -Uri $WebhookUrl",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected dry-run guard tokens: {missing}"
