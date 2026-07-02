from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import require_role
from .db import AsyncSessionLocal, get_session
from .models import (
    HumanRequest,
    HumanRequestList,
    HumanRequestOut,
    HumanRequestUpdate,
    KbEntry,
    KbEntryCreate,
    KbEntryList,
    KbEntryOut,
    KbEntryUpdate,
    Thread,
    UnansweredList,
    UnansweredOut,
    UnansweredQuestion,
    UnansweredUpdate,
    User,
)
from .providers import get_embeddings
from .tasks import reembed_entry

# ═══════════════════════════════════════════════════════════════
# Unanswered questions router
# ═══════════════════════════════════════════════════════════════

unanswered_router = APIRouter(tags=["admin"])


async def _enrich_unanswered(q: UnansweredQuestion, session: AsyncSession) -> UnansweredOut:
    out = UnansweredOut(
        id=q.id,
        thread_id=q.thread_id,
        message_id=q.message_id,
        query=q.query,
        top_sim=q.top_sim,
        reason=q.reason,
        resolved=q.resolved,
        created_at=q.created_at,
    )
    thread_result = await session.execute(select(Thread).where(Thread.id == q.thread_id))
    thread = thread_result.scalar_one_or_none()
    if thread:
        out.thread_title = thread.title
        user_result = await session.execute(select(User).where(User.id == thread.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            out.user_email = user.email
    return out


@unanswered_router.get("", response_model=UnansweredList)
async def list_unanswered(
    reason: Optional[str] = Query(None),
    resolved: Optional[bool] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(UnansweredQuestion).order_by(UnansweredQuestion.created_at.desc())
    if reason:
        stmt = stmt.where(UnansweredQuestion.reason == reason)
    if resolved is not None:
        stmt = stmt.where(UnansweredQuestion.resolved == resolved)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await session.execute(stmt)
    items = result.scalars().all()
    enriched = [await _enrich_unanswered(q, session) for q in items]
    return UnansweredList(items=enriched, total=total, page=page, size=size)


@unanswered_router.get("/{qid}", response_model=UnansweredOut)
async def get_unanswered(
    qid: uuid.UUID,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(UnansweredQuestion).where(UnansweredQuestion.id == qid))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    return await _enrich_unanswered(q, session)


@unanswered_router.patch("/{qid}", response_model=UnansweredOut)
async def update_unanswered(
    qid: uuid.UUID,
    body: UnansweredUpdate,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(UnansweredQuestion).where(UnansweredQuestion.id == qid))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    if body.resolved is not None:
        q.resolved = body.resolved
    await session.commit()
    await session.refresh(q)
    return await _enrich_unanswered(q, session)


@unanswered_router.delete("/{qid}", status_code=204)
async def delete_unanswered(
    qid: uuid.UUID,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(UnansweredQuestion).where(UnansweredQuestion.id == qid))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    await session.delete(q)
    await session.commit()
    return None


# ═══════════════════════════════════════════════════════════════
# Knowledge base router
# ═══════════════════════════════════════════════════════════════

kb_router = APIRouter(tags=["admin"])


async def _enrich_kb(entry: KbEntry) -> KbEntryOut:
    return KbEntryOut(
        id=entry.id,
        category=entry.category,
        title=entry.title,
        content=entry.content,
        updated_at=entry.updated_at,
        has_embedding=entry.embedding is not None,
    )


async def _reembed_background(entry_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as bg_session:
        await reembed_entry(entry_id, bg_session)


@kb_router.get("", response_model=KbEntryList)
async def list_kb(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(KbEntry).order_by(KbEntry.updated_at.desc())
    if category:
        stmt = stmt.where(KbEntry.category == category)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await session.execute(stmt)
    items = result.scalars().all()
    return KbEntryList(items=[await _enrich_kb(e) for e in items], total=total, page=page, size=size)


@kb_router.get("/{kid}", response_model=KbEntryOut)
async def get_kb_entry(
    kid: uuid.UUID,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(KbEntry).where(KbEntry.id == kid))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    return await _enrich_kb(entry)


@kb_router.post("", response_model=KbEntryOut, status_code=201)
async def create_kb_entry(
    body: KbEntryCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    entry = KbEntry(category=body.category, title=body.title, content=body.content)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    background_tasks.add_task(_reembed_background, entry.id)
    return await _enrich_kb(entry)


@kb_router.patch("/{kid}", response_model=KbEntryOut)
async def update_kb_entry(
    kid: uuid.UUID,
    body: KbEntryUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(KbEntry).where(KbEntry.id == kid))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    if body.category is not None:
        entry.category = body.category
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
        entry.embedding = None
    await session.commit()
    await session.refresh(entry)
    if body.content is not None:
        background_tasks.add_task(_reembed_background, entry.id)
    return await _enrich_kb(entry)


@kb_router.delete("/{kid}", status_code=204)
async def delete_kb_entry(
    kid: uuid.UUID,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(KbEntry).where(KbEntry.id == kid))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    await session.delete(entry)
    await session.commit()
    return None


# ═══════════════════════════════════════════════════════════════
# Human handoff router
# ═══════════════════════════════════════════════════════════════

handoff_router = APIRouter(tags=["admin"])


async def _enrich_handoff(hr: HumanRequest, session: AsyncSession) -> HumanRequestOut:
    out = HumanRequestOut(
        id=hr.id, user_id=hr.user_id, thread_id=hr.thread_id, status=hr.status, created_at=hr.created_at
    )
    user_result = await session.execute(select(User).where(User.id == hr.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        out.user_email = user.email
    thread_result = await session.execute(select(Thread).where(Thread.id == hr.thread_id))
    thread = thread_result.scalar_one_or_none()
    if thread:
        out.thread_title = thread.title
    return out


@handoff_router.get("", response_model=HumanRequestList)
async def list_handoffs(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(HumanRequest).order_by(HumanRequest.created_at.desc())
    if status:
        stmt = stmt.where(HumanRequest.status == status)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await session.execute(stmt)
    items = result.scalars().all()
    enriched = [await _enrich_handoff(hr, session) for hr in items]
    return HumanRequestList(items=enriched, total=total, page=page, size=size)


@handoff_router.get("/{hrid}", response_model=HumanRequestOut)
async def get_handoff(
    hrid: uuid.UUID,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(HumanRequest).where(HumanRequest.id == hrid))
    hr = result.scalar_one_or_none()
    if not hr:
        raise HTTPException(status_code=404, detail="Not found")
    return await _enrich_handoff(hr, session)


@handoff_router.patch("/{hrid}", response_model=HumanRequestOut)
async def update_handoff(
    hrid: uuid.UUID,
    body: HumanRequestUpdate,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(HumanRequest).where(HumanRequest.id == hrid))
    hr = result.scalar_one_or_none()
    if not hr:
        raise HTTPException(status_code=404, detail="Not found")
    if body.status is not None:
        hr.status = body.status
    await session.commit()
    await session.refresh(hr)
    return await _enrich_handoff(hr, session)


@handoff_router.delete("/{hrid}", status_code=204)
async def delete_handoff(
    hrid: uuid.UUID,
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(HumanRequest).where(HumanRequest.id == hrid))
    hr = result.scalar_one_or_none()
    if not hr:
        raise HTTPException(status_code=404, detail="Not found")
    await session.delete(hr)
    await session.commit()
    return None


# ═══════════════════════════════════════════════════════════════
# KB seeding
# ═══════════════════════════════════════════════════════════════


async def seed_kb(session: AsyncSession) -> int:
    seed_path = Path(os.path.dirname(__file__)) / ".." / ".." / "seed" / "mission_br.json"
    seed_path = seed_path.resolve()
    if not seed_path.exists():
        return 0
    with open(seed_path, encoding="utf-8") as f:
        entries = json.load(f)
    count = 0
    for entry in entries:
        result = await session.execute(select(KbEntry).where(KbEntry.title == entry["title"]))
        existing = result.scalar_one_or_none()
        if existing:
            continue
        kb = KbEntry(category=entry["category"], title=entry["title"], content=entry["content"])
        session.add(kb)
        count += 1
    await session.commit()
    embed_fn = get_embeddings().aembed_query
    for kb_entry in await _get_unembedded(session):
        vec = await embed_fn(kb_entry.content)
        kb_entry.embedding = vec
        kb_entry.fts = func.to_tsvector("portuguese", kb_entry.title + " " + kb_entry.content)
        await session.commit()
    return count


async def _get_unembedded(session: AsyncSession) -> list[KbEntry]:
    result = await session.execute(select(KbEntry).where(KbEntry.embedding.is_(None)))
    return list(result.scalars().all())


async def reembed_missing(session: AsyncSession) -> int:
    embed_fn = get_embeddings().aembed_query
    entries = await _get_unembedded(session)
    for entry in entries:
        vec = await embed_fn(entry.content)
        entry.embedding = vec
    await session.commit()
    return len(entries)
