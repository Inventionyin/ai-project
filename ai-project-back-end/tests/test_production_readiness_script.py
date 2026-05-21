import os
import shutil
import subprocess
from pathlib import Path
import pytest


def _powershell_executable() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        raise AssertionError("PowerShell executable not found")
    return executable


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in [
        "WEITESTING_APP_URL",
        "WEITESTING_API_URL",
        "WEITESTING_GRAFANA_URL",
        "WEITESTING_JENKINS_URL",
        "WEITESTING_PROMETHEUS_URL",
        "WEITESTING_JENKINS_BACKUP_DIR",
    ]:
        env.pop(name, None)
    return env


def test_production_readiness_script_contains_required_contract():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "verify_production_readiness.ps1"
    content = script_path.read_text(encoding="utf-8")

    required_tokens = [
        "param(",
        "[switch]$DryRun",
        "[switch]$FailOnWarn",
        "[string]$AppUrl",
        "[string]$ApiBaseUrl",
        "[string]$GrafanaUrl",
        "[string]$JenkinsUrl",
        "[string]$PrometheusUrl",
        "[string]$JenkinsBackupDir",
        "[string]$OutputPath",
        "Test-HttpEndpoint",
        "Test-PrometheusTargets",
        "Test-JenkinsBackup",
        "/health",
        "/api/health",
        "/api/v1/targets?state=active",
        "jenkins",
        "weitesting-backend",
        "READY",
        "WARN",
        "BLOCKED",
        "recommendedActions",
        "Verify Jenkins /prometheus returns 200",
        "Keep Jenkins and Grafana behind strong login or Cloudflare Access",
        "Production readiness gate failed (FailOnWarn enabled).",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected production readiness tokens: {missing}"


def test_production_readiness_dry_run_is_offline_and_documents_targets():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_production_readiness.ps1"

    result = subprocess.run(
        [
            _powershell_executable(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-DryRun",
            "-AppUrl",
            "https://app.example.com",
            "-ApiBaseUrl",
            "https://api.example.com",
            "-GrafanaUrl",
            "https://grafana.example.com",
            "-JenkinsUrl",
            "https://jenkins.example.com",
            "-PrometheusUrl",
            "http://127.0.0.1:9090",
            "-JenkinsBackupDir",
            "/tmp/jenkins-backups",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_clean_env(),
    )
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0
    assert "[DryRun] AppUrl: https://app.example.com" in output
    assert "[DryRun] ApiBaseUrl: https://api.example.com" in output
    assert "[DryRun] GrafanaUrl: https://grafana.example.com" in output
    assert "[DryRun] JenkinsUrl: https://jenkins.example.com" in output
    assert "[DryRun] PrometheusUrl: http://127.0.0.1:9090" in output
    assert "[DryRun] JenkinsBackupDir: /tmp/jenkins-backups" in output


def test_production_readiness_bash_script_contains_required_contract():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "verify_production_readiness.sh"
    content = script_path.read_text(encoding="utf-8")

    required_tokens = [
        "set -euo pipefail",
        "DRY_RUN=0",
        "FAIL_ON_WARN=0",
        "APP_URL=",
        "API_BASE_URL=",
        "GRAFANA_URL=",
        "JENKINS_URL=",
        "PROMETHEUS_URL=",
        "JENKINS_BACKUP_DIR=",
        "OUTPUT_PATH=",
        "urllib.request",
        "/health",
        "/api/health",
        "/api/v1/targets?state=active",
        "weitesting-backend",
        "jenkins",
        "READY",
        "WARN",
        "BLOCKED",
        "recommendedActions",
        "Verify Jenkins /prometheus returns 200",
        "Keep Jenkins and Grafana behind strong login or Cloudflare Access",
        "Production readiness gate failed (FailOnWarn enabled).",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected bash production readiness tokens: {missing}"


def test_production_readiness_bash_dry_run_is_offline_and_documents_targets():
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash executable not found")

    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "verify_production_readiness.sh"

    result = subprocess.run(
        [
            bash,
            str(script),
            "--dry-run",
            "--app-url",
            "https://app.example.com",
            "--api-base-url",
            "https://api.example.com",
            "--grafana-url",
            "https://grafana.example.com",
            "--jenkins-url",
            "https://jenkins.example.com",
            "--prometheus-url",
            "http://127.0.0.1:9090",
            "--jenkins-backup-dir",
            "/tmp/jenkins-backups",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_clean_env(),
    )
    output = f"{result.stdout}\n{result.stderr}"
    if "execvpe(/bin/bash) failed" in output:
        pytest.skip("bash executable is a WSL shim without a usable Linux bash")

    assert result.returncode == 0
    assert "[DryRun] AppUrl: https://app.example.com" in output
    assert "[DryRun] ApiBaseUrl: https://api.example.com" in output
    assert "[DryRun] GrafanaUrl: https://grafana.example.com" in output
    assert "[DryRun] JenkinsUrl: https://jenkins.example.com" in output
    assert "[DryRun] PrometheusUrl: http://127.0.0.1:9090" in output
    assert "[DryRun] JenkinsBackupDir: /tmp/jenkins-backups" in output
