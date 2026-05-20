import os
import shutil
from pathlib import Path
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


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
    "ZENTAO_ACCOUNT",
    "ZENTAO_PASSWORD",
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


def test_verify_external_integrations_supports_business_closure_guardrails():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"
    content = script.read_text(encoding="utf-8")

    required_tokens = [
        "[switch]$EnableBusinessClosure",
        "Invoke-BusinessClosureChecks",
        "WEITESTING_BUSINESS_CLOSURE_PREFIX",
        "[BUSINESS] Jira issue created",
        "[BUSINESS] Jenkins build trigger accepted",
        "[BUSINESS] Zentao bug created",
        "Business closure checks failed",
        "Business closure is disabled by default",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected business closure tokens: {missing}"


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


def test_verify_external_integrations_supports_jira_project_level_smoke():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"
    content = script.read_text(encoding="utf-8")

    required_tokens = [
        '$projectKey = [Environment]::GetEnvironmentVariable("JIRA_PROJECT_KEY")',
        '$encodedProjectKey = [System.Uri]::EscapeDataString($projectKey)',
        '$projectUri = "$base/rest/api/3/project/$encodedProjectKey"',
        'Invoke-RestMethod -Method Get -Uri $projectUri -Headers $headers -TimeoutSec 10 | Out-Null',
        'Write-Host ("[SMOKE] Jira project {0} reachable." -f $projectKey)',
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected Jira project smoke tokens: {missing}"


def test_verify_external_integrations_supports_dynamic_zentao_token():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"
    content = script.read_text(encoding="utf-8")

    required_tokens = [
        "function Get-ZentaoToken",
        'Invoke-RestMethod -Method Post -Uri "$BaseUrl/api.php/v1/tokens"',
        '"ZENTAO_ACCOUNT+ZENTAO_PASSWORD"',
        '"ZENTAO_PASSWORD"',
        "$token = Get-ZentaoToken -BaseUrl $base",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected Zentao dynamic token tokens: {missing}"


def test_verify_external_integrations_prefers_dynamic_zentao_token_when_credentials_exist():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_external_integrations.ps1"
    calls: list[tuple[str, str | None]] = []

    class ZentaoHandler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            calls.append(("POST", self.path))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"token":"fresh-token"}')

        def do_GET(self):  # noqa: N802
            calls.append(("GET", self.headers.get("token")))
            if self.headers.get("token") == "fresh-token":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"id":1}')
                return
            self.send_response(401)
            self.end_headers()

        def log_message(self, format, *args):  # noqa: A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ZentaoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = _clean_env()
        env.update(
            {
                "ZENTAO_BASE_URL": f"http://127.0.0.1:{server.server_port}",
                "ZENTAO_PRODUCT": "1",
                "ZENTAO_TOKEN": "expired-token",
                "ZENTAO_ACCOUNT": "account",
                "ZENTAO_PASSWORD": "password",
            }
        )
        result = subprocess.run(
            [
                _powershell_executable(),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-Targets",
                "Zentao",
                "-EnableSmoke",
                "-FailOnSmokeError",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
    finally:
        server.shutdown()
        server.server_close()

    output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, output
    assert "[SMOKE] Zentao product API reachable." in output
    assert ("POST", "/api.php/v1/tokens") in calls
    assert ("GET", "fresh-token") in calls
