from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from pydantic_settings import BaseSettings, SettingsConfigDict

current_dir = Path(__file__).resolve().parent

# 2. Go 4 levels up to hit the root_folder/
# app (1) -> src (2) -> api (3) -> apps (4) -> root_folder
ROOT_DIR = current_dir.parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    env: str = "dev"
    log_level: str = "info"

    database_url: str = "postgresql+asyncpg://aiagent:aiagent@localhost:5432/aiagent"

    jwt_secret: str = "changeme"
    jwt_ttl_hours: int = 24
    admin_email: str = "admin@admin.com"
    auth_dev_fallback: bool = True

    # Cookie
    cookie_name: str = "auth_token"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""

    embedding_dim: int = 384

    mcp_url: str = "http://mcp:8000/mcp"
    mcp_fetch_timeout_seconds: int = 20

    rate_limit_ip_per_min: int = 30
    rate_limit_user_per_min: int = 20
    rate_limit_login_per_min: int = 10

    web_origin: str = "http://localhost:5173"
    max_body_bytes: int = 16384

    rag_unanswered_threshold: float = 0.55
    rag_top_k: int = 5

    cache_sim_threshold: float = 0.85
    cache_ttl_seconds: int = 86400

    handoff_threshold: float = 0.70

    enable_llm_titles: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
print(settings)


def create_access_token(email: str, role: str, user_id: str | None = None) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": email,
        "role": role,
        "exp": now + timedelta(hours=settings.jwt_ttl_hours),
        "iat": now,
    }
    if user_id:
        payload["id"] = user_id
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def _extract_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
    return auth.removeprefix("Bearer ")


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        try:
            token = _extract_token(request)
        except HTTPException:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


def require_role(required: str):
    async def _require(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
        user_role = current_user.get("role", "user")
        if required == "admin" and user_role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        return current_user

    return _require
