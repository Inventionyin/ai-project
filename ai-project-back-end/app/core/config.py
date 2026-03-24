from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = str(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai-test-platform"
    env: str = "local"
    debug: bool = False

    api_prefix: str = "/api"

    database_url: str = "postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_platform"

    cors_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"

    secrets_encryption_key: str = ""

    jwt_secret_key: str = Field(default="", validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_in: int = 7200
    runner_workspace_root: str = ""
    runner_python_executable: str = "python"
    runner_allure_command: str = "allure"
    runner_allure_runs_root: str = ""

    # LLM Configuration
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

