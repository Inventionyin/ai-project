from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = str(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai-test-platform"
    env: str = "local"
    debug: bool = False

    api_prefix: str = "/api"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_test_platform"

    cors_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"

    secrets_encryption_key: str = ""

    jwt_secret_key: str = Field(default="", validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_in: int = 7200
    auth_header_impersonation_enabled: bool = False
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
    notification_outbox_consumer_enabled: bool = True
    notification_outbox_poll_interval_seconds: float = 2.0
    notification_outbox_batch_size: int = 20
    notification_outbox_retry_base_seconds: int = 5

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "t", "yes", "y", "on", "debug", "dev", "local"}:
                return True
            if normalized in {"0", "false", "f", "no", "n", "off", "release", "prod", "production"}:
                return False
            return False
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()

