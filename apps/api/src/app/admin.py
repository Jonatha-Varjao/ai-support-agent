from __future__ import annotations

import asyncio
import json
from pathlib import Path
import uuid
from typing import Optional

import mlflow
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import ROOT_DIR as _ROOT_DIR
from .config import CurrentUser, require_role
from .db import AsyncSessionLocal, get_session
from .models import (
    AdminThreadList,
    AdminThreadOut,
    HandoffStatus,
    HumanRequest,
    HumanRequestList,
    HumanRequestOut,
    HumanRequestUpdate,
    KbEntry,
    KbEntryCreate,
    KbEntryList,
    KbEntryOut,
    KbEntryUpdate,
    Message,
    MessageOut,
    Thread,
    UnansweredList,
    UnansweredOut,
    UnansweredQuestion,
    UnansweredReason,
    UnansweredUpdate,
    User,
)
from .providers import get_embeddings
from .tasks import reembed_entry

EMBED_BATCH_SIZE = 100


async def _get_or_404(session: AsyncSession, model, id: uuid.UUID):
    item = await session.get(model, id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item


async def _paginate(session: AsyncSession, stmt, page: int, size: int):
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await session.execute(stmt)
    items = result.scalars().all()
    return items, total


# ═══════════════════════════════════════════════════════════════
# Unanswered questions router
# ═══════════════════════════════════════════════════════════════

unanswered_router = APIRouter(tags=["admin"])


async def _enrich_thread_user(session: AsyncSession, thread_id) -> tuple[str | None, str | None]:
    result = await session.execute(
        select(Thread.title, User.email).join(User, Thread.user_id == User.id).where(Thread.id == thread_id)
    )
    row = result.one_or_none()
    if row:
        return row.title, row.email
    return None, None


async def _batch_enrich_thread_user(session: AsyncSession, thread_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[str | None, str | None]]:
    if not thread_ids:
        return {}
    result = await session.execute(
        select(Thread.id, Thread.title, User.email)
        .join(User, Thread.user_id == User.id)
        .where(Thread.id.in_(thread_ids))
    )
    return {row.id: (row.title, row.email) for row in result.all()}


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
    out.thread_title, out.user_email = await _enrich_thread_user(session, q.thread_id)
    return out


@unanswered_router.get("", response_model=UnansweredList)
async def list_unanswered(
    reason: Optional[UnansweredReason] = Query(None),
    resolved: Optional[bool] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(UnansweredQuestion).order_by(UnansweredQuestion.created_at.desc(), UnansweredQuestion.id.desc())
    if reason:
        stmt = stmt.where(UnansweredQuestion.reason == reason)
    if resolved is not None:
        stmt = stmt.where(UnansweredQuestion.resolved == resolved)
    items, total = await _paginate(session, stmt, page, size)
    id_map = await _batch_enrich_thread_user(session, [q.thread_id for q in items])
    enriched = []
    for q in items:
        title, email = id_map.get(q.thread_id, (None, None))
        enriched.append(UnansweredOut(
            id=q.id, thread_id=q.thread_id, message_id=q.message_id, query=q.query,
            top_sim=q.top_sim, reason=q.reason, resolved=q.resolved, created_at=q.created_at,
            user_email=email, thread_title=title,
        ))
    return UnansweredList(items=enriched, total=total, page=page, size=size)


@unanswered_router.get("/{qid}", response_model=UnansweredOut)
async def get_unanswered(
    qid: uuid.UUID,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    q = await _get_or_404(session, UnansweredQuestion, qid)
    return await _enrich_unanswered(q, session)


@unanswered_router.patch("/{qid}", response_model=UnansweredOut)
async def update_unanswered(
    qid: uuid.UUID,
    body: UnansweredUpdate,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    q = await _get_or_404(session, UnansweredQuestion, qid)
    if body.resolved is not None:
        q.resolved = body.resolved
    await session.commit()
    await session.refresh(q)
    return await _enrich_unanswered(q, session)


@unanswered_router.delete("/{qid}", status_code=204)
async def delete_unanswered(
    qid: uuid.UUID,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    q = await _get_or_404(session, UnansweredQuestion, qid)
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
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(KbEntry).order_by(KbEntry.updated_at.desc(), KbEntry.id.desc())
    if category:
        stmt = stmt.where(KbEntry.category == category)
    items, total = await _paginate(session, stmt, page, size)
    return KbEntryList(items=[await _enrich_kb(e) for e in items], total=total, page=page, size=size)


@kb_router.get("/{kid}", response_model=KbEntryOut)
async def get_kb_entry(
    kid: uuid.UUID,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    entry = await _get_or_404(session, KbEntry, kid)
    return await _enrich_kb(entry)


@kb_router.post("", response_model=KbEntryOut, status_code=201)
async def create_kb_entry(
    body: KbEntryCreate,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    entry = KbEntry(category=body.category, title=body.title, content=body.content)
    entry.fts = func.to_tsvector("portuguese", entry.title + " " + entry.content)
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
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    entry = await _get_or_404(session, KbEntry, kid)
    if body.category is not None:
        entry.category = body.category
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
        entry.embedding = None
    if body.title is not None or body.content is not None:
        entry.fts = func.to_tsvector("portuguese", entry.title + " " + entry.content)
    await session.commit()
    await session.refresh(entry)
    if body.content is not None:
        background_tasks.add_task(_reembed_background, entry.id)
    return await _enrich_kb(entry)


@kb_router.delete("/{kid}", status_code=204)
async def delete_kb_entry(
    kid: uuid.UUID,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    entry = await _get_or_404(session, KbEntry, kid)
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
    out.thread_title, out.user_email = await _enrich_thread_user(session, hr.thread_id)
    return out


@handoff_router.get("", response_model=HumanRequestList)
async def list_handoffs(
    status: Optional[HandoffStatus] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(HumanRequest).order_by(HumanRequest.created_at.desc(), HumanRequest.id.desc())
    if status:
        stmt = stmt.where(HumanRequest.status == status)
    items, total = await _paginate(session, stmt, page, size)
    id_map = await _batch_enrich_thread_user(session, [hr.thread_id for hr in items])
    enriched = []
    for hr in items:
        title, email = id_map.get(hr.thread_id, (None, None))
        enriched.append(HumanRequestOut(
            id=hr.id, user_id=hr.user_id, thread_id=hr.thread_id, status=hr.status, created_at=hr.created_at,
            user_email=email, thread_title=title,
        ))
    return HumanRequestList(items=enriched, total=total, page=page, size=size)


@handoff_router.get("/{hrid}", response_model=HumanRequestOut)
async def get_handoff(
    hrid: uuid.UUID,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    hr = await _get_or_404(session, HumanRequest, hrid)
    return await _enrich_handoff(hr, session)


@handoff_router.patch("/{hrid}", response_model=HumanRequestOut)
async def update_handoff(
    hrid: uuid.UUID,
    body: HumanRequestUpdate,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    hr = await _get_or_404(session, HumanRequest, hrid)
    if body.status is not None:
        hr.status = body.status
    await session.commit()
    await session.refresh(hr)
    return await _enrich_handoff(hr, session)


@handoff_router.delete("/{hrid}", status_code=204)
async def delete_handoff(
    hrid: uuid.UUID,
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    hr = await _get_or_404(session, HumanRequest, hrid)
    await session.delete(hr)
    await session.commit()
    return None


# ═══════════════════════════════════════════════════════════════
# KB seeding
# ═══════════════════════════════════════════════════════════════


@mlflow.trace(span_type="TASK")
async def seed_kb(session: AsyncSession) -> int:
    seed_path = _ROOT_DIR / "apps" / "api" / "seed" / "mission_br.json"
    if not seed_path.exists():
        return 0
    content = await asyncio.to_thread(Path(seed_path).read_text, encoding="utf-8")
    entries = json.loads(content)
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
    embeddings = get_embeddings()
    unembedded = await _get_unembedded(session)
    for i in range(0, len(unembedded), EMBED_BATCH_SIZE):
        batch = unembedded[i : i + EMBED_BATCH_SIZE]
        texts = [e.content for e in batch]
        vectors = await embeddings.aembed_documents(texts)
        for kb_entry, vec in zip(batch, vectors):
            kb_entry.embedding = vec
            kb_entry.fts = func.to_tsvector("portuguese", kb_entry.title + " " + kb_entry.content)
        await session.commit()
    return count


async def _get_unembedded(session: AsyncSession) -> list[KbEntry]:
    result = await session.execute(select(KbEntry).where(KbEntry.embedding.is_(None)))
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════
# Admin threads router
# ═══════════════════════════════════════════════════════════════

threads_router = APIRouter(tags=["admin"])


@threads_router.get("", response_model=AdminThreadList)
async def list_all_threads(
    user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Thread).order_by(Thread.updated_at.desc(), Thread.id.desc())
    if user_id:
        stmt = stmt.where(Thread.user_id == uuid.UUID(user_id))
    items, total = await _paginate(session, stmt, page, size)
    id_map = await _batch_enrich_thread_user(session, [t.id for t in items])
    enriched = [
        AdminThreadOut(id=t.id, title=t.title, user_email=id_map.get(t.id, (None, None))[1] or "—", updated_at=t.updated_at)
        for t in items
    ]
    return AdminThreadList(items=enriched, total=total, page=page, size=size)


@threads_router.get("/{thread_id}/messages", response_model=list[MessageOut])
async def get_admin_thread_messages(
    thread_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user: CurrentUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Thread).where(Thread.id == thread_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Thread não encontrado")
    stmt = select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at.asc(), Message.id.asc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    messages = result.scalars().all()
    return [
        MessageOut(
            id=m.id,
            thread_id=m.thread_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]
