from __future__ import annotations

import uuid
from dataclasses import dataclass
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
    database_url: str = "postgresql+asyncpg://aiagent:aiagent@localhost:5432/aiagent"

    jwt_secret: str = "changeme"
    jwt_ttl_hours: int = 24
    admin_email: str = "admin@admin.com"

    # Cookie
    cookie_name: str = "auth_token"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    gemini_api_key: str = ""

    embedding_dim: int = 384

    mcp_url: str = "http://mcp:8000/mcp"
    company_website_url: str = ""

    web_origin: str = "http://localhost:5173"

    rag_top_k: int = 5

    cache_sim_threshold: float = 0.95

    handoff_threshold: float = 0.70
    rag_unanswered_threshold: float = 0.35
    history_char_budget: int = 3000
    history_msg_limit: int = 20
    vector_weight: float = 0.85

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MLflow
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_experiment_name: str = "ai-support-agent-v2"


settings = Settings()


@dataclass
class CurrentUser:
    id: uuid.UUID
    email: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


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


async def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        token = _extract_token(request)
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not in token")
    return CurrentUser(
        id=uuid.UUID(user_id),
        email=payload.get("sub", "unknown"),
        role=payload.get("role", "user"),
    )


def require_role(required: str):
    async def _require(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if required == "admin" and not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        return user
    return _require
