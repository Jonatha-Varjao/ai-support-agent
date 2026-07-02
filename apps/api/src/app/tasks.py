from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import KbEntry
from .providers import get_embeddings


async def reembed_entry(entry_id: uuid.UUID, session: AsyncSession) -> None:
    """Re-embed a KB entry. Designed to run as a FastAPI BackgroundTask.

    This is the single seam for future broker/queue evolution: swap this
    function body for a publish-to-queue call without touching callers.
    """
    result = await session.execute(select(KbEntry).where(KbEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return
    text = entry.content
    vec = await get_embeddings().aembed_query(text)
    entry.embedding = vec
    await session.commit()
