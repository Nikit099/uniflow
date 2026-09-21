import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db import (
    Case,
    MaxIdentity,
    Membership,
    NotificationOutbox,
    Organization,
    ProcessedWebhook,
    User,
    get_db,
)

router = APIRouter(prefix="/integrations/max", tags=["MAX"])


def _sender(update: dict[str, Any]) -> dict[str, Any]:
    message = update.get("message") or {}
    return message.get("sender") or update.get("user") or update.get("sender") or {}


def _text(update: dict[str, Any]) -> str:
    message = update.get("message") or {}
    body = message.get("body") or {}
    return str(body.get("text") or message.get("text") or "").strip()


def _open_attachment(
    settings: Settings, label: str, case_id: str | None = None
) -> list[dict[str, object]]:
    suffix = f"?startapp=case_{case_id[:8]}" if case_id else ""
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [{"type": "link", "text": label, "url": f"{settings.public_base_url}/{suffix}"}]
                ]
            },
        }
    ]


async def _identity(
    db: AsyncSession, update: dict[str, Any], settings: Settings
) -> MaxIdentity | None:
    sender = _sender(update)
    max_user_id = sender.get("user_id") or sender.get("id")
    if max_user_id is None:
        return None
    identity = await db.scalar(
        select(MaxIdentity).where(MaxIdentity.max_user_id == str(max_user_id))
    )
    if identity:
        return identity
    user = User(
        display_name=str(sender.get("name") or sender.get("first_name") or "MAX user"),
        preferred_language=str(sender.get("language_code") or "ru")[:5],
    )
    db.add(user)
    await db.flush()
    identity = MaxIdentity(
        user_id=user.id,
        max_user_id=str(max_user_id),
        username=sender.get("username"),
        first_name=str(sender.get("first_name") or sender.get("name") or "MAX user"),
        last_name=sender.get("last_name"),
        language_code=sender.get("language_code"),
    )
    db.add(identity)
    if settings.demo_mode:
        organization = await db.scalar(
            select(Organization).where(Organization.slug == "demo-university")
        )
        if organization:
            db.add(Membership(user_id=user.id, organization_id=organization.id, role="STUDENT"))
    return identity


@router.post("/webhook", status_code=200)
async def webhook(
    update: dict[str, Any],
    x_max_bot_api_secret: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if settings.max_webhook_secret and not hmac.compare_digest(
        x_max_bot_api_secret or "", settings.max_webhook_secret
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MAX webhook secret")
    update_id = str(update.get("update_id") or update.get("message_id") or "")
    processed = await db.get(ProcessedWebhook, update_id) if update_id else None
    if not update_id or processed:
        return Response(status_code=200)
    db.add(ProcessedWebhook(update_id=update_id))
    identity = await _identity(db, update, settings)
    if identity:
        user = await db.get(User, identity.user_id)
        assert user is not None
        command = _text(update).lower().split(maxsplit=1)[0]
        active_case = await db.scalar(
            select(Case)
            .where(Case.student_user_id == user.id, Case.status.not_in(["COMPLETED", "CANCELLED"]))
            .order_by(Case.updated_at.desc())
        )
        ru = user.preferred_language != "en"
        if command == "/language":
            user.preferred_language = "en" if ru else "ru"
            text = "Language changed to English." if ru else "Язык изменён на русский."
        elif command == "/help":
            text = (
                "Команды: /start, /cases, /language. UniFlow помогает подготовить комплект для проверки университетом."
                if ru
                else "Commands: /start, /cases, /language. UniFlow helps prepare a package for university review."
            )
        elif command == "/cases":
            text = (
                (f"Активное дело: {active_case.status}." if active_case else "Активных дел нет.")
                if ru
                else (f"Active case: {active_case.status}." if active_case else "No active cases.")
            )
        elif command in {"/start", ""}:
            attention = active_case and active_case.status == "CHANGES_REQUESTED"
            if ru:
                text = (
                    "Добро пожаловать в UniFlow. Есть действие, которое требует внимания."
                    if attention
                    else "Добро пожаловать в UniFlow. Откройте приложение, чтобы увидеть следующее действие."
                )
            else:
                text = (
                    "Welcome to UniFlow. An action needs your attention."
                    if attention
                    else "Welcome to UniFlow. Open the app to see your next action."
                )
        else:
            text = (
                "В проверенных источниках системы недостаточно информации для надёжного ответа. Откройте дело или отправьте вопрос сотруднику."
                if ru
                else "Verified sources do not contain enough information for a reliable answer. Open the case or ask staff."
            )
        label = "Открыть UniFlow" if ru else "Open UniFlow"
        db.add(
            NotificationOutbox(
                event_type="BOT_REPLY",
                recipient_user_id=user.id,
                payload={
                    "text": text,
                    "attachments": _open_attachment(
                        settings, label, active_case.id if active_case else None
                    ),
                },
            )
        )
    await db.commit()
    return Response(status_code=200)
