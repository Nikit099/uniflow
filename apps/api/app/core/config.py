from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    public_base_url: str = "http://localhost:8080"
    database_url: str = "sqlite+aiosqlite:///./uniflow.db"
    session_secret: str = "demo-session-secret-change-in-production"
    session_ttl_hours: int = 24
    demo_mode: bool = True
    demo_auth_enabled: bool = True
    demo_seed: bool = True
    file_storage_path: Path = Path("./uploads")
    file_max_size_mb: int = 10
    max_enabled: bool = False
    max_api_base_url: str = "https://platform-api2.max.ru"
    max_bot_token: str = ""
    max_webapp_auth_max_age_seconds: int = 3600
    llm_enabled: bool = False
    llm_config_path: Path = Path("../../config/llm-profiles.yaml")
    llm_primary_base_url: str = ""
    llm_primary_api_key: str = ""
    llm_primary_model: str = ""
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:8080,http://localhost:5173"

    @model_validator(mode="after")
    def production_safety(self) -> "Settings":
        if self.app_env == "production":
            errors: list[str] = []
            if (
                self.session_secret == "demo-session-secret-change-in-production"
                or len(self.session_secret) < 32
            ):
                errors.append("SESSION_SECRET must be a strong non-default value")
            if self.demo_auth_enabled or self.demo_mode:
                errors.append("demo features must be disabled")
            if not self.public_base_url.startswith("https://"):
                errors.append("PUBLIC_BASE_URL must use HTTPS")
            if "demo_only" in self.database_url:
                errors.append("demo database password is forbidden")
            if errors:
                raise ValueError("Unsafe production configuration: " + "; ".join(errors))
        return self

    @property
    def origins(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
