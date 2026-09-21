from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import OfficialSource


async def search_verified_sources(
    db: AsyncSession, organization_id: str, query: str, limit: int = 5
) -> list[OfficialSource]:
    terms = [term for term in query.replace("?", " ").split() if len(term) >= 4][:6]
    statement = select(OfficialSource).where(
        OfficialSource.organization_id == organization_id, OfficialSource.status == "VERIFIED"
    )
    if terms:
        statement = statement.where(
            or_(*[OfficialSource.excerpt.ilike(f"%{term}%") for term in terms])
        )
    return list((await db.scalars(statement.limit(limit))).all())
