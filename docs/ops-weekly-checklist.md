# Weekly Operations Checklist

Use this as the short-run checklist for post-acceptance operation.

## Daily

- [ ] Check the latest performance baseline report under `/opt/weitesting/artifacts/performance-baseline/`
- [ ] Check the latest production readiness report under `/opt/weitesting/artifacts/production-readiness/`
- [ ] Check the latest Jenkins restore drill result under `/opt/weitesting/artifacts/jenkins-restore-drill/`
- [ ] Confirm no new `BLOCKED` result appeared
- [ ] If one path gets `WARN` twice in a row, open an investigation task

## Weekly

- [ ] Import the newest requirement / testcase / defect batch in the UI
- [ ] Open `/projects/:projectId/trial-operation`
- [ ] Review duplicate testcase suggestions
- [ ] Review low-value testcase suggestions
- [ ] Review P0 / P1 defects and owners
- [ ] Review suites without a default environment
- [ ] Run one key regression suite and confirm the run detail page is readable
- [ ] Export or save a new acceptance snapshot

## Monthly

- [ ] Re-run external integration smoke
- [ ] Re-run business closure if the external systems are expected to accept test records
- [ ] Re-check backup / restore evidence
- [ ] Compare the latest performance trend with the previous month
- [ ] Confirm the production readiness page still matches the deployed environment

## Before External Demo Or Release Change

- [ ] Re-run production readiness
- [ ] Re-run real external smoke
- [ ] Confirm Jenkins, Jira, Zentao, and DingTalk are all `READY`
- [ ] Save fresh evidence links in the signoff index

## If Something Fails

- `WARN` twice on the same path: create a performance investigation task
- Restore drill failure: treat as a readiness blocker
- External smoke failure: check token expiry, VPN, base URL, and permissions
- Data import mismatch: keep source files and record the import result

## Evidence Links

- [Post-Acceptance Operations SOP](./post-acceptance-operations-sop.md)
- [Operations Rerun Record - 2026-05-26](./operations-rerun-20260526.md)
