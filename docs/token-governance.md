# Token Governance

WeiTesting separates CI trigger tokens from external system token material.

## Named CI Token

- A Named CI Token belongs to one project and one automation purpose, for example `jenkins-main` or `github-nightly`.
- The backend stores only hash and hint; plaintext is shown once during creation or rotation.
- Token state can be active, disabled, expired, revoked, or leaked.
- Policies can restrict runner types, allowed test cases, and maximum test case count.

## External System Token

External system token values for Jira, Zentao, Jenkins, DingTalk, GitHub, SMTP, or similar providers should be treated as deployment secrets:

- store them in GitHub Actions secrets, server environment variables, or a secret manager
- never commit them to `.env`, docs, screenshots, or generated reports
- rotate them after setup sessions where values were pasted into chat or terminals
- keep owner, provider, environment, expiry, and rotation date in an ops inventory

## Rotation

- Rotate CI tokens whenever a runner is decommissioned, a log leak is suspected, or a maintainer leaves the project.
- Rotate external system tokens after initial integration smoke tests and before production acceptance.
- Attach rotation evidence to the production readiness report when a token protects a production system.

## Expiry

- Prefer expiring tokens for CI runners and external integrations.
- The UI highlights expiry risk for Named CI Token records.
- External system token expiry is still operated from the provider side; keep provider reminders in the ops inventory until a unified secret registry exists.

## Current Boundary

- Named CI Token lifecycle is implemented in the product.
- External system token governance is documented and validated by integration scripts, but not yet a full in-product secret manager.
