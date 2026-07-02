from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import (
    create_access_token,
    get_current_user,
    settings,
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
        max_age=settings.jwt_ttl_hours * 3600,
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
async def me(current_user: Annotated[dict, Depends(get_current_user)]):
    return UserOut(
        id=current_user.get("id", "unknown"),
        email=current_user["sub"],
        role=current_user["role"],
    )
