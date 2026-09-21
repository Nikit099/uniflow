from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    max_webhook_secret: str = ""
    max_webapp_auth_max_age_seconds: int = 3600
    llm_enabled: bool = False
    llm_config_path: Path = Path("../../config/llm-profiles.yaml")
    llm_provider: Literal["openai_compatible", "gigachat", "routerai"] = "openai_compatible"
    llm_primary_base_url: str = ""
    llm_primary_api_key: str = ""
    llm_primary_model: str = ""
    llm_gigachat_authorization_key: str = ""
    llm_gigachat_scope: str = "GIGACHAT_API_PERS"
    llm_gigachat_base_url: str = "https://api.giga.chat/v1"
    llm_gigachat_oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    llm_gigachat_model: str = "GigaChat-3-Ultra"
    llm_routerai_base_url: str = "https://routerai.ru/api/v1"
    llm_routerai_api_key: str = ""
    llm_routerai_model: str = ""
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:8080,http://localhost:5173"

    @model_validator(mode="after")
    def production_safety(self) -> "Settings":
        if self.llm_enabled:
            llm_errors: list[str] = []
            if self.llm_provider == "gigachat" and not self.llm_gigachat_authorization_key:
                llm_errors.append("LLM_GIGACHAT_AUTHORIZATION_KEY is required for GigaChat")
            if self.llm_provider == "gigachat" and not self.llm_gigachat_model:
                llm_errors.append("LLM_GIGACHAT_MODEL is required for GigaChat")
            if self.llm_provider == "routerai" and not self.llm_routerai_api_key:
                llm_errors.append("LLM_ROUTERAI_API_KEY is required for RouterAI")
            if self.llm_provider == "routerai" and not self.llm_routerai_model:
                llm_errors.append("LLM_ROUTERAI_MODEL is required for RouterAI")
            if self.llm_provider == "openai_compatible" and (
                not self.llm_primary_base_url
                or not self.llm_primary_api_key
                or not self.llm_primary_model
            ):
                llm_errors.append(
                    "LLM_PRIMARY_BASE_URL, LLM_PRIMARY_API_KEY and LLM_PRIMARY_MODEL are required"
                )
            if llm_errors:
                raise ValueError("Invalid LLM configuration: " + "; ".join(llm_errors))
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
            if self.max_enabled and len(self.max_webhook_secret) < 5:
                errors.append("MAX_WEBHOOK_SECRET is required when MAX is enabled")
            if errors:
                raise ValueError("Unsafe production configuration: " + "; ".join(errors))
        return self

    @property
    def origins(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
