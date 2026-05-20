from pathlib import Path


def test_real_e2e_workflow_contains_required_ci_entrypoints():
    repo_root = Path(__file__).resolve().parents[2]
    workflow_path = repo_root / ".github" / "workflows" / "real-e2e.yml"
    content = workflow_path.read_text(encoding="utf-8")

    required_tokens = [
        "Run backend pytest + frontend build + generated E2E",
        "./scripts/verify_real_e2e.ps1",
        "Run performance baseline dry-run",
        "./scripts/run_performance_baseline.ps1 -DryRun",
        "Run external integrations diagnostics dry-run (if script exists)",
        "./scripts/verify_external_integrations.ps1 -DryRun",
        "includeExternalSmoke",
        "includeExternalBusinessClosure",
        "Run external integrations smoke (manual only)",
        "inputs.includeExternalSmoke",
        "JIRA_BASE_URL: ${{ vars.JIRA_BASE_URL }}",
        "JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}",
        '$args = @("-Targets", $env:EXTERNAL_SMOKE_TARGETS, "-EnableSmoke", "-FailOnSmokeError")',
        "./scripts/verify_external_integrations.ps1 @args",
        "EXTERNAL_SMOKE_TARGETS: ${{ inputs.externalSmokeTargets }}",
        "ENABLE_EXTERNAL_BUSINESS_CLOSURE: ${{ inputs.includeExternalBusinessClosure }}",
        "-EnableBusinessClosure",
        "externalSmokeTargets",
        "Run frontend real E2E (workflow_dispatch or nightly)",
        "github.event_name == 'schedule'",
        "includeFrontendRealE2E",
        "actions/checkout@v6",
        "actions/setup-python@v6",
        "actions/setup-node@v6",
        "permissions:",
        "contents: read",
        "timeout-minutes: 45",
        "concurrency:",
        "cancel-in-progress: true",
        "- dev",
        "- main",
        "- master",
    ]

    missing = [token for token in required_tokens if token not in content]
    assert not missing, f"Missing expected workflow tokens: {missing}"
