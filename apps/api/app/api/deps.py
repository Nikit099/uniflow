from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import token_hash, verify_origin
from app.db import Membership, Session, User, get_db


@dataclass(frozen=True)
class Actor:
    user: User
    organization_id: str
    role: str


async def current_actor(
    request: Request,
    uniflow_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> Actor:
    if not uniflow_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    row = await db.execute(
        select(Session, User, Membership)
        .join(User, User.id == Session.user_id)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Session.token_hash == token_hash(uniflow_session),
            Session.revoked_at.is_(None),
            Session.expires_at > datetime.now(timezone.utc),
            User.active.is_(True),
        )
    )
    value = row.first()
    if not value:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    session, user, membership = value
    request.state.session = session
    request.state.actor = user
    request.state.organization_id = membership.organization_id
    return Actor(user, membership.organization_id, membership.role)


def require_roles(*roles: str):  # type: ignore[no-untyped-def]
    async def dependency(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return actor

    return dependency


async def mutation_guard(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    actor: Actor = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> Actor:
    if not verify_origin(request.headers.get("origin"), settings):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid origin")
    if x_csrf_token != request.state.session.csrf_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid CSRF token")
    return actor


def mutation_roles(*roles: str):  # type: ignore[no-untyped-def]
    async def dependency(actor: Actor = Depends(mutation_guard)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return actor

    return dependency
