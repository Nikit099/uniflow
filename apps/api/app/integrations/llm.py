import json
from abc import ABC, abstractmethod
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
