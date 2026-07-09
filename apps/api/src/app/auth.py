from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import (
    create_access_token,
    get_current_user,
    settings,
    CurrentUser,
)
from .db import get_session
from .models import User


class LoginRequest(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    id: str
    email: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    user: UserOut


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Demo-only auth flow. In production, add password or OAuth verification."""
    email = request.email
    role = "admin" if email == settings.admin_email else "user"

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(email=email, role=role)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    elif role == "admin" and user.role != "admin":
        user.role = "admin"
        await session.commit()
        await session.refresh(user)

    token = create_access_token(email, user.role, str(user.id))
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=int(timedelta(hours=settings.jwt_ttl_hours).total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    return LoginResponse(
        access_token=token,
        user=UserOut(id=str(user.id), email=user.email, role=user.role),
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(settings.cookie_name)
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser = Depends(get_current_user)):
    return UserOut(
        id=str(user.id),
        email=user.email,
        role=user.role,
    )
