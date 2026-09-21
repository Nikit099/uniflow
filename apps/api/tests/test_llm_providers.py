from app.core.config import Settings
from app.integrations.llm import GigaChatProvider, OpenAICompatibleProvider, get_llm_provider


def test_provider_factory_selects_gigachat() -> None:
    provider = get_llm_provider(
        Settings(
            llm_enabled=True,
            llm_provider="gigachat",
            llm_gigachat_authorization_key="not-a-real-secret",
        )
    )
    assert isinstance(provider, GigaChatProvider)


def test_provider_factory_selects_routerai() -> None:
    provider = get_llm_provider(
        Settings(
            llm_enabled=True,
            llm_provider="routerai",
            llm_routerai_api_key="not-a-real-secret",
            llm_routerai_model="deepseek/example",
        )
    )
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://routerai.ru/api/v1"
    assert provider.model == "deepseek/example"
