from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Actor, current_actor
from app.db import OfficialSource, get_db

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/{source_id}")
async def source(
    source_id: str,
    actor: Actor = Depends(current_actor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    item = await db.scalar(
        select(OfficialSource).where(
            OfficialSource.id == source_id,
            OfficialSource.organization_id == actor.organization_id,
            OfficialSource.status == "VERIFIED",
        )
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    return {
        "id": item.id,
        "title": item.title,
        "issuer": item.issuer,
        "url": item.url,
        "excerpt": item.excerpt,
        "status": item.status,
        "last_verified_at": item.last_verified_at,
        "origin": "UNIVERSITY_CONFIG",
    }
