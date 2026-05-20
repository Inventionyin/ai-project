# Backend E2E Tests

These tests exercise the real FastAPI app, real auth, and a real PostgreSQL database.

Run from `ai-project-back-end`:

```powershell
$env:PYTHONPATH='.'
$env:TEST_DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/ai_test_platform_e2e'
python scripts/setup_test_db.py --reset
pytest tests/e2e -v
```

Safety guard: the database name must contain `test` or `e2e`; otherwise the setup script refuses to create, reset, or drop it.
