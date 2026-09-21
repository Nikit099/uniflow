import json
import time
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ValidationError


class GroundedAnswer(BaseModel):
    answer: str
    source_ids: list[str]
    uncertainty: Literal["LOW", "MEDIUM", "HIGH"]
    needs_human: bool


class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def complete_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                },
            )
            response.raise_for_status()
            return json.loads(response.json()["choices"][0]["message"]["content"])


class GigaChatProvider(LLMProvider):
    """GigaChat v1 adapter with in-memory OAuth access-token refresh."""

    def __init__(
        self,
        authorization_key: str,
        scope: str,
        base_url: str,
        oauth_url: str,
        model: str,
        timeout: float = 20.0,
    ) -> None:
        self.authorization_key = authorization_key
        self.scope = scope
        self.base_url = base_url.rstrip("/")
        self.oauth_url = oauth_url
        self.model = model
        self.timeout = timeout
        self._access_token = ""
        self._expires_at = 0.0

    async def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token

        authorization = self.authorization_key
        if not authorization.lower().startswith("basic "):
            authorization = f"Basic {authorization}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.oauth_url,
                headers={
                    "Accept": "application/json",
                    "Authorization": authorization,
                    "RqUID": str(uuid.uuid4()),
                },
                data={"scope": self.scope},
            )
            response.raise_for_status()
            token_data = response.json()

        access_token = token_data.get("access_token")
        expires_at = token_data.get("expires_at")
        if not isinstance(access_token, str) or not isinstance(expires_at, int | float):
            raise ValueError("GigaChat OAuth response did not contain an access token")
        # GigaChat documents seconds; support millisecond timestamps defensively.
        self._access_token = access_token
        self._expires_at = float(expires_at) / (1000 if expires_at > 10_000_000_000 else 1)
        return self._access_token

    async def complete_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        access_token = await self._get_access_token()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "model": self.model,
                    "response_format": {
                        "type": "json_schema",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "answer": {"type": "string"},
                                "source_ids": {"type": "array", "items": {"type": "string"}},
                                "uncertainty": {
                                    "type": "string",
                                    "enum": ["LOW", "MEDIUM", "HIGH"],
                                },
                                "needs_human": {"type": "boolean"},
                            },
                            "required": ["answer", "source_ids", "uncertainty", "needs_human"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                },
            )
            response.raise_for_status()
            return json.loads(response.json()["choices"][0]["message"]["content"])


@lru_cache(maxsize=3)
def _provider_from_config(
    provider_name: str,
    primary_base_url: str,
    primary_api_key: str,
    primary_model: str,
    gigachat_authorization_key: str,
    gigachat_scope: str,
    gigachat_base_url: str,
    gigachat_oauth_url: str,
    gigachat_model: str,
    routerai_base_url: str,
    routerai_api_key: str,
    routerai_model: str,
) -> LLMProvider:
    if provider_name == "gigachat":
        return GigaChatProvider(
            gigachat_authorization_key,
            gigachat_scope,
            gigachat_base_url,
            gigachat_oauth_url,
            gigachat_model,
        )
    if provider_name == "routerai":
        return OpenAICompatibleProvider(routerai_base_url, routerai_api_key, routerai_model)
    return OpenAICompatibleProvider(primary_base_url, primary_api_key, primary_model)


def get_llm_provider(settings: Any) -> LLMProvider:
    """Select a provider without exposing its credential beyond the backend process."""
    return _provider_from_config(
        settings.llm_provider,
        settings.llm_primary_base_url,
        settings.llm_primary_api_key,
        settings.llm_primary_model,
        settings.llm_gigachat_authorization_key,
        settings.llm_gigachat_scope,
        settings.llm_gigachat_base_url,
        settings.llm_gigachat_oauth_url,
        settings.llm_gigachat_model,
        settings.llm_routerai_base_url,
        settings.llm_routerai_api_key,
        settings.llm_routerai_model,
    )


def parse_grounded_answer(value: dict[str, Any], allowed_sources: set[str]) -> GroundedAnswer:
    try:
        answer = GroundedAnswer.model_validate(value)
    except ValidationError as exc:
        raise ValueError("Invalid structured LLM output") from exc
    if not set(answer.source_ids).issubset(allowed_sources):
        raise ValueError("LLM referenced an unverified source")
    if not answer.source_ids:
        answer.uncertainty = "HIGH"
        answer.needs_human = True
    return answer
