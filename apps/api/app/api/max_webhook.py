from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import ProcessedWebhook, get_db

router = APIRouter(prefix="/integrations/max", tags=["MAX"])


@router.post("/webhook", status_code=204)
async def webhook(update: dict[str, object], db: AsyncSession = Depends(get_db)) -> Response:
    update_id = str(update.get("update_id") or update.get("message_id") or "")
    if not update_id:
        return Response(status_code=204)
    if await db.get(ProcessedWebhook, update_id):
        return Response(status_code=204)
    db.add(ProcessedWebhook(update_id=update_id))
    await db.commit()
    return Response(status_code=204)
