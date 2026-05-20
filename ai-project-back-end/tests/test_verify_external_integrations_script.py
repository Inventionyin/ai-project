import os
import shutil
from pathlib import Path
import subprocess


_INTEGRATION_ENV_NAMES = [
    "DINGTALK_WEBHOOK_URL",
    "GITHUB_TOKEN",
    "GITHUB_REPOSITORY",
    "GITHUB_WORKFLOW_FILE",
    "WEITESTING_GITHUB_TOKEN",
    "WEITESTING_GITHUB_REPOSITORY",
    "WEITESTING_GITHUB_WORKFLOW_FILE",
    "JENKINS_BASE_URL",
    "JENKINS_JOB_NAME",
    "JENKINS_USERNAME",
    "JENKINS_API_TOKEN",
    "JIRA_BASE_URL",
    "JIRA_PROJECT_KEY",
    "JIRA_EMAIL",
    "JIRA_TOKEN",
    "ZENTAO_BASE_URL",
    "ZENTAO_PRODUCT",
    "ZENTAO_TOKEN",
]


def _powershell_executable() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        raise AssertionError("PowerShell executable not found")
    return executable


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in _INTEGRATION_ENV_NAMES:
        env.pop(name, None)
    return env


def _run_ps(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_powershell_executable(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_clean_env(),
    )


def test_verify_external_integrations_help():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"

    result = _run_ps(script, ["-Help"])
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0
    assert "Usage: .\\scripts\\verify_external_integrations.ps1" in output
    assert "-DryRun" in output
    assert "DINGTALK_WEBHOOK_URL" in output


def test_verify_external_integrations_supports_signed_dingtalk_smoke():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"
    content = script.read_text(encoding="utf-8")

    required_tokens = [
        "DINGTALK_WEBHOOK_SECRET",
        "Get-DingTalkSignedWebhookUrl",
        "[System.Security.Cryptography.HMACSHA256]::new",
        "timestamp=",
        "sign=",
        "Invoke-RestMethod -Method Post -Uri $signedWebhook",
        "WeiTesting external integration smoke",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected DingTalk signature smoke tokens: {missing}"


def test_verify_external_integrations_dry_run_shows_missing():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"

    result = _run_ps(script, ["-DryRun"])
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0
    assert "[DingTalk] MISSING" in output
    assert "[GitHub Actions] MISSING" in output
    assert "[Jenkins] MISSING" in output
    assert "[Jira] MISSING" in output
    assert "[Zentao] MISSING" in output
    assert "Missing env: DINGTALK_WEBHOOK_URL" in output
    assert "No external API calls were made." in output


def test_verify_external_integrations_uses_non_reserved_github_env_aliases():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"

    env = _clean_env()
    env.update(
        {
            "WEITESTING_GITHUB_TOKEN": "token",
            "WEITESTING_GITHUB_REPOSITORY": "Inventionyin/ai-project",
            "WEITESTING_GITHUB_WORKFLOW_FILE": ".github/workflows/real-e2e.yml",
        }
    )
    result = subprocess.run(
        [_powershell_executable(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-DryRun"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0
    assert "[GitHub Actions] READY" in output
    assert "Missing env: WEITESTING_GITHUB_TOKEN" not in output


def test_verify_external_integrations_can_target_jira_only():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"

    env = _clean_env()
    env.update(
        {
            "JIRA_BASE_URL": "https://aitestplatform.atlassian.net",
            "JIRA_PROJECT_KEY": "AIT",
            "JIRA_EMAIL": "user@example.com",
            "JIRA_TOKEN": "token",
        }
    )
    result = subprocess.run(
        [_powershell_executable(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-DryRun", "-Targets", "Jira"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0
    assert "[Jira] READY" in output
    assert "[DingTalk]" not in output
    assert "[Jenkins]" not in output


def test_verify_external_integrations_handles_empty_smoke_failures_list():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"
    content = script.read_text(encoding="utf-8")

    assert "@(Invoke-SmokeChecks -Statuses $statuses)" in content
