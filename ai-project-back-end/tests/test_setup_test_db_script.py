import asyncio

from scripts import setup_test_db


def test_main_runs_migrations_after_async_database_setup(monkeypatch):
    calls = []

    async def fake_ensure_database(url, *, reset=False, drop=False):
        asyncio.get_running_loop()
        calls.append(("ensure", url, reset, drop))

    def fake_run_migrations(url):
        with pytest_raises_running_loop_absent():
            asyncio.get_running_loop()
        calls.append(("migrate", url))

    class pytest_raises_running_loop_absent:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return exc_type is RuntimeError and "no running event loop" in str(exc)

    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_test_platform_e2e")
    monkeypatch.setattr(setup_test_db, "ensure_database", fake_ensure_database)
    monkeypatch.setattr(setup_test_db, "run_migrations", fake_run_migrations)
    monkeypatch.setattr("sys.argv", ["setup_test_db.py"])

    setup_test_db.main()

    assert calls == [
        (
            "ensure",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_test_platform_e2e",
            False,
            False,
        ),
        ("migrate", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_test_platform_e2e"),
    ]


def test_main_skips_migrations_for_drop(monkeypatch):
    calls = []

    async def fake_ensure_database(url, *, reset=False, drop=False):
        calls.append(("ensure", reset, drop))

    def fake_run_migrations(url):
        calls.append(("migrate", url))

    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_test_platform_e2e")
    monkeypatch.setattr(setup_test_db, "ensure_database", fake_ensure_database)
    monkeypatch.setattr(setup_test_db, "run_migrations", fake_run_migrations)
    monkeypatch.setattr("sys.argv", ["setup_test_db.py", "--drop"])

    setup_test_db.main()

    assert calls == [("ensure", False, True)]
