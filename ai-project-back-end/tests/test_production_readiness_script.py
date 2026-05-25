import os
import shutil
import subprocess
import threading
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
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
        "Test-ObservabilityRuleFiles",
        "alert-rules.yml",
        "/health",
        "/metrics",
        "api-metrics",
        "app-same-origin-api",
        "/api/projects",
        '"code":40101',
        "weitesting_observability_ready",
        "/api/health",
        "/api/v1/targets?state=active",
        "jenkins",
        "weitesting-backend",
        "READY",
        "WARN",
        "BLOCKED",
        "recommendedActions",
        "Repo-local /metrics is checked separately",
        "Keep Jenkins and Grafana behind strong login or Cloudflare Access",
        "Production readiness gate failed (FailOnWarn enabled).",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected production readiness tokens: {missing}"


def test_nginx_template_proxies_app_api_to_backend_before_spa_fallback():
    repo_root = Path(__file__).resolve().parents[2]
    template = (repo_root / "deploy" / "nginx" / "weitesting.conf.template").read_text(encoding="utf-8")

    app_server_start = template.index("server_name ${APP_DOMAIN};")
    api_proxy_start = template.index("location /api/", app_server_start)
    spa_fallback_start = template.index("location / {", app_server_start)

    assert api_proxy_start < spa_fallback_start
    assert "proxy_pass http://127.0.0.1:8000" in template[api_proxy_start:spa_fallback_start]
    assert "X-Forwarded-Proto $scheme" in template[api_proxy_start:spa_fallback_start]


def test_python_spa_server_proxies_api_before_index_fallback(tmp_path):
    import importlib.util
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    repo_root = Path(__file__).resolve().parents[2]
    server_path = repo_root / "deploy" / "frontend" / "spa_server.py"
    spec = importlib.util.spec_from_file_location("weitesting_spa_server", server_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class BackendHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"code":40101,"message":"Not authenticated"}')

        def log_message(self, format, *args):
            return

    backend = ThreadingHTTPServer(("127.0.0.1", 0), BackendHandler)
    backend_thread = threading.Thread(target=backend.serve_forever, daemon=True)
    backend_thread.start()

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text('<div id="app"></div>', encoding="utf-8")
    (dist / "asset.txt").write_text("asset", encoding="utf-8")

    module.ROOT = dist.resolve()
    module.API_UPSTREAM = f"http://127.0.0.1:{backend.server_port}"
    module.API_UPSTREAM_PARSED = urlparse(module.API_UPSTREAM)
    frontend = ThreadingHTTPServer(("127.0.0.1", 0), module.SpaHandler)
    frontend_thread = threading.Thread(target=frontend.serve_forever, daemon=True)
    frontend_thread.start()

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{frontend.server_port}/api/projects", timeout=5) as response:
            assert response.status == 200
            assert response.read().decode("utf-8") == '{"code":40101,"message":"Not authenticated"}'

        with urllib.request.urlopen(f"http://127.0.0.1:{frontend.server_port}/projects/demo", timeout=5) as response:
            assert response.status == 200
            assert '<div id="app"></div>' in response.read().decode("utf-8")
    finally:
        frontend.shutdown()
        backend.shutdown()


def test_observability_alert_rules_and_slo_docs_are_committed():
    repo_root = Path(__file__).resolve().parents[2]
    prometheus = (repo_root / "deploy" / "observability" / "prometheus.yml").read_text(encoding="utf-8")
    alert_rules = (repo_root / "deploy" / "observability" / "alert-rules.yml").read_text(encoding="utf-8")
    slo_doc = (repo_root / "docs" / "slo.md").read_text(encoding="utf-8")
    sandbox_doc = (repo_root / "docs" / "plugin-sandbox-boundary.md").read_text(encoding="utf-8")
    token_doc = (repo_root / "docs" / "token-governance.md").read_text(encoding="utf-8")

    assert "rule_files:" in prometheus
    assert "alert-rules.yml" in prometheus
    for token in [
        "WeiTestingApiDown",
        "WeiTestingHighServerErrorRate",
        "WeiTestingObservabilityNotReady",
        "weitesting_observability_ready",
    ]:
        assert token in alert_rules
    for token in ["Availability", "Latency", "Error Budget", "Notification Outbox", "CI Token"]:
        assert token in slo_doc
    for token in ["process-level", "not a container", "CALL_EXTERNAL", "allowedHosts"]:
        assert token in sandbox_doc
    for token in ["Named CI Token", "external system token", "rotation", "expiry"]:
        assert token in token_doc


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
        errors="replace",
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
        "test_observability_rule_files",
        "alert-rules.yml",
        "/health",
        "/metrics",
        "api-metrics",
        "app-same-origin-api",
        "/api/projects",
        '"code":40101',
        "weitesting_observability_ready",
        "/api/health",
        "/api/v1/targets?state=active",
        "weitesting-backend",
        "jenkins",
        "READY",
        "WARN",
        "BLOCKED",
        "recommendedActions",
        "Repo-local /metrics is checked separately",
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
        errors="replace",
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
