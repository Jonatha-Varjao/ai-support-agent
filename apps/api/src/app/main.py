from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin import (
    handoff_router,
    kb_router,
    unanswered_router,
)
from .auth import router as auth_router
from .chat import router as chat_router
from .config import settings
from .db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .chat import get_phrase_embeddings
    from .db import run_migrations
    from .providers import warmup_embeddings

    await run_migrations()

    # async with AsyncSessionLocal() as session:
    #     from .admin import seed_kb as _seed_kb
    #     await _seed_kb(session)

    await get_phrase_embeddings()
    await warmup_embeddings()

    app.state.redis = None
    redis_url = getattr(settings, "redis_url", None)
    if redis_url:
        import redis.asyncio as aioredis

        try:
            app.state.redis = aioredis.from_url(redis_url, decode_responses=True)
        except Exception:
            pass

    from .chat import init_cache as _init_cache
    from .chat import init_mcp_client

    _init_cache(redis_url=getattr(settings, "redis_url", None))
    init_mcp_client()

    yield

    if app.state.redis:
        await app.state.redis.close()
    await engine.dispose()


app = FastAPI(
    title="AI Support Agent — Mission",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(chat_router, tags=["chat"])
app.include_router(unanswered_router, prefix="/admin/unanswered", tags=["admin"])
app.include_router(kb_router, prefix="/admin/kb", tags=["admin"])
app.include_router(handoff_router, prefix="/admin/handoffs", tags=["admin"])


import logging
import traceback

logger = logging.getLogger("uvicorn.error")


@app.exception_handler(Exception)
async def log_unhandled_exceptions(request, exc):
    logger.error(
        "Unhandled on %s %s:\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
async def health():
    return {"status": "ok"}
