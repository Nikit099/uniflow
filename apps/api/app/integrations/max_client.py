from abc import ABC, abstractmethod
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import DemoNotification


class MaxClient(ABC):
    @abstractmethod
    async def send(self, user_id: str, event_type: str, payload: dict[str, Any]) -> None: ...


class RealMaxClient(MaxClient):
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    async def send(self, user_id: str, event_type: str, payload: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers={"Authorization": self.token},
                params={"user_id": user_id},
                json={
                    "text": payload.get("text", event_type),
                    "attachments": payload.get("attachments", []),
                },
            )
            response.raise_for_status()


class FakeMaxClient(MaxClient):
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def send(self, user_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.db.add(
            DemoNotification(recipient_user_id=user_id, event_type=event_type, payload=payload)
        )
