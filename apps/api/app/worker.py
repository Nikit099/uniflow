import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db import MaxIdentity, NotificationOutbox, Session, SessionFactory
from app.integrations.max_client import FakeMaxClient, MaxClient, RealMaxClient


async def process_once() -> int:
    settings = get_settings()
    async with SessionFactory() as db:
        statement = (
            select(NotificationOutbox)
            .where(
                NotificationOutbox.status.in_(["PENDING", "FAILED"]),
                NotificationOutbox.next_attempt_at <= datetime.now(timezone.utc),
            )
            .limit(20)
            .with_for_update(skip_locked=True)
        )
        events = list((await db.scalars(statement)).all())
        for event in events:
            event.status = "PROCESSING"
        await db.commit()
        for event in events:
            try:
                if settings.max_enabled:
                    identity = await db.scalar(
                        select(MaxIdentity).where(MaxIdentity.user_id == event.recipient_user_id)
                    )
                    if not identity:
                        raise ValueError("Recipient has no MAX identity")
                    client: MaxClient = RealMaxClient(
                        settings.max_api_base_url, settings.max_bot_token
                    )
                    recipient = identity.max_user_id
                else:
                    client = FakeMaxClient(db)
                    recipient = event.recipient_user_id
                await client.send(recipient, event.event_type, event.payload)
                event.status = "SENT"
                event.sent_at = datetime.now(timezone.utc)
            except Exception as exc:
                event.attempt_count += 1
                event.status = "FAILED"
                event.last_error = type(exc).__name__
                event.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                    seconds=min(3600, 2**event.attempt_count)
                )
        await db.execute(delete(Session).where(Session.expires_at < datetime.now(timezone.utc)))
        await db.commit()
        return len(events)


async def run() -> None:
    while True:
        await process_once()
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run())
