from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Actor, current_actor, mutation_guard
from app.core.config import Settings, get_settings
from app.core.security import (
    InvalidMaxLaunch,
    csrf_token,
    token_hash,
    token_urlsafe,
    validate_max_init_data,
)
from app.db import MaxIdentity, Membership, Organization, Session, User, get_db
from app.schemas import DemoLogin, MaxLogin, UserView

router = APIRouter(prefix="/auth", tags=["auth"])
password_hasher = PasswordHasher()


async def _new_session(db: AsyncSession, user_id: str, settings: Settings) -> tuple[str, Session]:
    raw = token_urlsafe()
    session = Session(
        user_id=user_id,
        token_hash=token_hash(raw),
        csrf_token=csrf_token(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    await db.flush()
    return raw, session


def _set_cookie(response: Response, raw: str, settings: Settings) -> None:
    response.set_cookie(
        "uniflow_session",
        raw,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


@router.post("/demo/login", response_model=UserView)
async def demo_login(
    body: DemoLogin,
    response: Response,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> UserView:
    if settings.app_env == "production" or not settings.demo_auth_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    aliases = {
        "student": "student@demo.local",
        "staff": "staff@demo.local",
        "org_admin": "admin@demo.local",
    }
    email = aliases.get(body.role)
    if not email:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown demo role")
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Demo data is not initialized")
    membership = await db.scalar(select(Membership).where(Membership.user_id == user.id))
    if not membership:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Demo membership missing")
    raw, session = await _new_session(db, user.id, settings)
    await db.commit()
    _set_cookie(response, raw, settings)
    return UserView(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        preferred_language=user.preferred_language,
        role=membership.role,
        organization_id=membership.organization_id,
        csrf_token=session.csrf_token,
    )


@router.post("/max", response_model=UserView)
async def max_login(
    body: MaxLogin,
    response: Response,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> UserView:
    if not settings.max_enabled or not settings.max_bot_token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "MAX integration is disabled")
    try:
        launch = validate_max_init_data(
            body.init_data, settings.max_bot_token, settings.max_webapp_auth_max_age_seconds
        )
    except InvalidMaxLaunch as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    identity = await db.scalar(
        select(MaxIdentity).where(MaxIdentity.max_user_id == launch.max_user_id)
    )
    if identity:
        user = await db.get(User, identity.user_id)
        assert user is not None
        identity.last_authenticated_at = datetime.now(timezone.utc)
    else:
        user = User(
            display_name=" ".join(filter(None, [launch.first_name, launch.last_name])),
            preferred_language=launch.language_code or "ru",
        )
        db.add(user)
        await db.flush()
        db.add(
            MaxIdentity(
                user_id=user.id,
                max_user_id=launch.max_user_id,
                username=launch.username,
                first_name=launch.first_name,
                last_name=launch.last_name,
                language_code=launch.language_code,
            )
        )
        if settings.demo_mode:
            organization = await db.scalar(
                select(Organization).where(Organization.slug == "demo-university")
            )
            if not organization:
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE, "Demo organization missing"
                )
            db.add(Membership(user_id=user.id, organization_id=organization.id, role="STUDENT"))
    membership = await db.scalar(select(Membership).where(Membership.user_id == user.id))
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "An organization invitation is required")
    raw, session = await _new_session(db, user.id, settings)
    await db.commit()
    _set_cookie(response, raw, settings)
    return UserView(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        preferred_language=user.preferred_language,
        role=membership.role,
        organization_id=membership.organization_id,
        csrf_token=session.csrf_token,
    )


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    request: Request,
    _: Actor = Depends(mutation_guard),
    db: AsyncSession = Depends(get_db),
) -> None:
    request.state.session.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    response.delete_cookie("uniflow_session", path="/")


@router.get("/me", response_model=UserView)
async def me(request: Request, actor: Actor = Depends(current_actor)) -> UserView:
    return UserView(
        id=actor.user.id,
        display_name=actor.user.display_name,
        email=actor.user.email,
        preferred_language=actor.user.preferred_language,
        role=actor.role,
        organization_id=actor.organization_id,
        csrf_token=request.state.session.csrf_token,
    )
