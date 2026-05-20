# CI Entrypoints (Real E2E + Dry-Run Diagnostics)

## `real-e2e` workflow

Primary CI workflow: `.github/workflows/real-e2e.yml`

The workflow now provides these entrypoints:

1. `./scripts/verify_real_e2e.ps1`
   - Covers backend `pytest`, frontend production build, and generated Playwright tests.
2. `./scripts/run_performance_baseline.ps1 -DryRun`
   - Verifies performance baseline script wiring without requiring live external systems.
3. `./scripts/verify_external_integrations.ps1 -DryRun` (only when script exists)
   - Runs external integration configuration diagnostics in dry-run mode.
   - If the script is absent, CI logs a skip notice and still passes.
4. Optional workflow-dispatch frontend real E2E
   - Runs full frontend real E2E only when manually requested with `includeFrontendRealE2E=true`.

## Secretless CI principle

CI should pass without real third-party secrets.
External integration checks in CI must use dry-run/configuration diagnostics mode.
