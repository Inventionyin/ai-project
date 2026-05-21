# E2E Tests (Real Database)

These tests run against a real PostgreSQL database with actual Alembic migrations applied.
They validate the full request→service→database→response chain.

## Prerequisites

- PostgreSQL running (Docker or local)
- Python dependencies installed (`pip install -r requirements.txt`)
- `allure` command available (optional, for report generation)

## Quick Start

```bash
# From ai-project-back-end/ directory

# 1. Set the test database URL (default: same credentials as .env, DB name ai_test_e2e)
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_e2e"

# 2. Run E2E tests
pytest tests/e2e -v

# 3. Run with Allure reporting
pytest tests/e2e --alluredir=allure-results -v
```

## What the conftest does

1. **Creates** the `ai_test_e2e` database (if it does not exist)
2. **Runs** `alembic upgrade head` against it
3. **Overrides** the app's `DATABASE_URL` so all requests hit the test DB
4. **Drops** the test database after the session completes

This means each test session starts with a clean schema. No manual setup needed.

## Test files

| File | Coverage |
|------|----------|
| `test_auth_e2e.py` | Register → Login → Me → Logout, duplicate detection, wrong password |
| `test_project_testcase_e2e.py` | Project CRUD, testcase creation, suite with cases |
| `test_worker_run_e2e.py` | Worker register/heartbeat, poll job, report results, run status transitions |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_DATABASE_URL` | `postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_e2e` | Test DB connection string |

## Notes

- Tests use `anyio` (not `asyncio`) for async pytest support.
- Each test gets a fresh session with automatic rollback, but the DB schema persists across tests.
- The worker E2E tests are timing-dependent — if no job is available on poll, they skip gracefully.
- These tests do NOT mock the database, auth, or any service layer. They are true integration tests.
