# CI Entrypoints (Real E2E + Dry-Run Diagnostics)

## `real-e2e` workflow

Primary CI workflow: `.github/workflows/real-e2e.yml`

Triggers:

1. `pull_request`
2. `push` to `dev`, `main`, or `master`
3. `workflow_dispatch`
4. nightly `schedule`

The workflow now provides these entrypoints:

1. `./scripts/verify_real_e2e.ps1`
   - Covers backend `pytest`, frontend production build, and generated Playwright tests.
2. `./scripts/run_performance_baseline.ps1 -DryRun`
   - Verifies performance baseline script wiring without requiring live external systems.
3. `./scripts/verify_external_integrations.ps1 -DryRun` (only when script exists)
   - Runs external integration configuration diagnostics in dry-run mode.
   - If the script is absent, CI logs a skip notice and still passes.
4. Optional/manual + nightly frontend real E2E
   - Runs full frontend real E2E when manually requested with `includeFrontendRealE2E=true`.
   - Runs full frontend real E2E on the nightly schedule.
5. Optional/manual external integration smoke
   - Runs live external API probes only when manually requested with `includeExternalSmoke=true`.
   - Defaults to `externalSmokeTargets=Jira`, so partially configured repositories can verify Jira first without requiring DingTalk/Jenkins/Zentao.
   - Injects repository Secrets/Variables into `verify_external_integrations.ps1 -EnableSmoke -FailOnSmokeError`.
   - Normal pull request, push, and nightly CI keep using dry-run diagnostics and do not call third-party systems.

## GitHub Repository Settings

Repository URL: `https://github.com/Inventionyin/ai-project`

Actions secrets live at:

```text
https://github.com/Inventionyin/ai-project/settings/secrets/actions
```

Use **Secrets** for sensitive values:

- `DINGTALK_WEBHOOK_URL`
- `DINGTALK_WEBHOOK_SECRET` if the DingTalk robot uses signature verification
- `WEITESTING_GITHUB_TOKEN` only when testing GitHub REST integration outside GitHub Actions with a PAT
- `JENKINS_API_TOKEN`
- `JIRA_TOKEN`
- `ZENTAO_TOKEN`

Use **Variables** for non-sensitive values:

- Do not create `GITHUB_*` variables in GitHub repository settings. GitHub reserves that prefix.
- GitHub Actions injects `WEITESTING_GITHUB_REPOSITORY`, `WEITESTING_GITHUB_WORKFLOW_FILE`, and `WEITESTING_GITHUB_TOKEN` automatically for this workflow.
- For local diagnostics only, set `WEITESTING_GITHUB_REPOSITORY=Inventionyin/ai-project` and `WEITESTING_GITHUB_WORKFLOW_FILE=.github/workflows/real-e2e.yml`.
- `JENKINS_BASE_URL`
- `JENKINS_JOB_NAME`
- `JENKINS_USERNAME`
- `JIRA_BASE_URL`
- `JIRA_PROJECT_KEY`
- `JIRA_EMAIL`
- `ZENTAO_BASE_URL`
- `ZENTAO_PRODUCT`

GitHub MCP and `gh` CLI are developer tooling. They are useful for creating PRs, triggering workflows, and reading logs, but CI itself only needs workflow YAML plus repository secrets/variables.

## Secretless CI principle

CI should pass without real third-party secrets.
External integration checks in CI must use dry-run/configuration diagnostics mode.

## CI Security Baseline

The `real-e2e` workflow keeps a small security baseline:

- `permissions: contents: read`
- `concurrency` per workflow/ref with `cancel-in-progress: true`
- `timeout-minutes: 45` on the verification job
- third-party actions use current major runtime tags (`actions/*@v6`)

For higher-assurance environments, pin third-party actions to immutable commit SHAs and review the pin on a scheduled cadence.

External smoke checks are opt-in:

```powershell
.\scripts\verify_external_integrations.ps1 -EnableSmoke
.\scripts\verify_external_integrations.ps1 -EnableSmoke -FailOnSmokeError
```

Use `-FailOnSmokeError` only when the target external systems are expected to be reachable and the token set is complete.

To run live external smoke from GitHub Actions:

```powershell
gh workflow run real-e2e --repo Inventionyin/ai-project --ref dev -f includeFrontendRealE2E=false -f includeExternalSmoke=true -f externalSmokeTargets=Jira
```

## Delivery Commands

```powershell
gh workflow run real-e2e --repo Inventionyin/ai-project --ref dev -f includeFrontendRealE2E=false
gh workflow run real-e2e --repo Inventionyin/ai-project --ref dev -f includeFrontendRealE2E=true
gh workflow run real-e2e --repo Inventionyin/ai-project --ref dev -f includeFrontendRealE2E=false -f includeExternalSmoke=true -f externalSmokeTargets=Jira
gh run list --repo Inventionyin/ai-project --workflow real-e2e --limit 10
gh run watch <run-id> --repo Inventionyin/ai-project --exit-status
gh run view <run-id> --repo Inventionyin/ai-project --log-failed
gh run rerun <run-id> --repo Inventionyin/ai-project --failed
```
