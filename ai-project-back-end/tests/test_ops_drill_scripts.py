from pathlib import Path


def test_jenkins_restore_drill_script_contract():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "deploy" / "jenkins" / "restore_drill_jenkins.sh"
    content = script_path.read_text(encoding="utf-8")

    required_tokens = [
        "set -euo pipefail",
        "BACKUP_DIR=",
        "DRILL_DIR=",
        "LATEST_BACKUP=",
        "--backup-file",
        "--drill-dir",
        "--output-path",
        "tar -tzf",
        "tar -xzf",
        "config.xml",
        "jobs",
        "plugins",
        "restoreDrill",
        "READY",
        "BLOCKED",
        "This drill never writes into JENKINS_HOME",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected Jenkins restore drill tokens: {missing}"


def test_install_ops_cron_script_contract():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "deploy" / "ops" / "install_ops_cron.sh"
    content = script_path.read_text(encoding="utf-8")

    required_tokens = [
        "set -euo pipefail",
        "REPO_DIR=",
        "LOG_DIR=",
        "ARTIFACT_DIR=",
        "/etc/cron.d/weitesting-ops",
        "verify_production_readiness.sh",
        "run_performance_baseline.ps1",
        "performance-baseline",
        "production-readiness",
        "Jenkins restore drill",
        "RESTORE_DRILL_ENABLED",
        "DingTalk",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected ops cron tokens: {missing}"


def test_performance_baseline_bash_script_contract():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_performance_baseline.sh"
    content = script_path.read_text(encoding="utf-8")

    required_tokens = [
        "set -euo pipefail",
        "API_BASE_URL=",
        "FRONTEND_URL=",
        "OUTPUT_PATH=",
        "TREND_PATH=",
        "ITERATIONS=",
        "BUSINESS_PATHS=",
        "--fail-on-warn",
        "--dry-run",
        "urllib.request",
        "p50Ms",
        "p95Ms",
        "maxMs",
        "errorCount",
        "trend-summary",
        "READY",
        "WARN",
        "BLOCKED",
        "Performance baseline gate failed (FailOnWarn enabled).",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected bash performance baseline tokens: {missing}"
