import pytest

from app.core.config import Settings


def test_production_allows_explicit_demo_login_without_demo_mode() -> None:
    settings = Settings(
        app_env="production",
        public_base_url="https://demo.example.test",
        database_url="postgresql+asyncpg://uniflow:strong-db-password@db:5432/uniflow",
        session_secret="production-session-secret-that-is-long-enough-123",
        demo_mode=False,
        demo_auth_enabled=True,
    )

    assert settings.demo_auth_enabled is True
    assert settings.demo_mode is False


def test_production_still_rejects_demo_mode() -> None:
    with pytest.raises(ValueError, match="DEMO_MODE must be disabled"):
        Settings(
            app_env="production",
            public_base_url="https://demo.example.test",
            database_url="postgresql+asyncpg://uniflow:strong-db-password@db:5432/uniflow",
            session_secret="production-session-secret-that-is-long-enough-123",
            demo_mode=True,
            demo_auth_enabled=True,
        )
