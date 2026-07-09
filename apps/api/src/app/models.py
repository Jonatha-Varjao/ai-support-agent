from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import settings as _settings

EMBEDDING_DIM = _settings.embedding_dim

KbCategory = Literal["product", "service", "flow", "institutional", "faq"]
HandoffStatus = Literal["open", "contacted", "closed"]
UnansweredReason = Literal["no_context", "injection"]

# ═══════════════════════════════════════════════════════════════
# ORM models
# ═══════════════════════════════════════════════════════════════


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user", server_default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    threads: Mapped[list["Thread"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    human_requests: Mapped[list["HumanRequest"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="threads")
    messages: Mapped[list["Message"]] = relationship(back_populates="thread", cascade="all, delete-orphan")
    unanswered_questions: Mapped[list["UnansweredQuestion"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )
    human_requests: Mapped[list["HumanRequest"]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant', 'tool')", name="ck_messages_role"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    thread: Mapped["Thread"] = relationship(back_populates="messages")
    unanswered_questions: Mapped[list["UnansweredQuestion"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class KbEntry(Base):
    __tablename__ = "kb_entries"
    __table_args__ = (
        CheckConstraint("category IN ('product', 'service', 'flow', 'institutional', 'faq')", name="ck_kb_category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    fts: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class UnansweredQuestion(Base):
    __tablename__ = "unanswered_questions"
    __table_args__ = (CheckConstraint("reason IN ('no_context', 'injection')", name="ck_unanswered_reason"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    top_sim: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False, default="no_context", server_default="no_context")
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    thread: Mapped["Thread"] = relationship(back_populates="unanswered_questions")
    message: Mapped["Message"] = relationship(back_populates="unanswered_questions")


class HumanRequest(Base):
    __tablename__ = "human_requests"
    __table_args__ = (CheckConstraint("status IN ('open', 'contacted', 'closed')", name="ck_human_status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", server_default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="human_requests")
    thread: Mapped["Thread"] = relationship(back_populates="human_requests")


# ═══════════════════════════════════════════════════════════════
# Pydantic schemas
# ═══════════════════════════════════════════════════════════════


class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    content: str = Field(..., max_length=4000)


class ThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    updated_at: datetime


class AdminThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    user_email: str
    updated_at: datetime


class AdminThreadList(BaseModel):
    items: list[AdminThreadOut]
    total: int
    page: int
    size: int


class ThreadRename(BaseModel):
    title: str = Field(..., max_length=100)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class UnansweredOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thread_id: uuid.UUID
    message_id: uuid.UUID
    query: str
    top_sim: float
    reason: UnansweredReason
    resolved: bool
    created_at: datetime
    user_email: Optional[str] = None
    thread_title: Optional[str] = None


class UnansweredList(BaseModel):
    items: list[UnansweredOut]
    total: int
    page: int
    size: int


class UnansweredUpdate(BaseModel):
    resolved: Optional[bool] = None


class HumanRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    thread_id: uuid.UUID
    status: HandoffStatus
    created_at: datetime
    user_email: Optional[str] = None
    thread_title: Optional[str] = None


class HumanRequestList(BaseModel):
    items: list[HumanRequestOut]
    total: int
    page: int
    size: int


class HumanRequestUpdate(BaseModel):
    status: Optional[HandoffStatus] = None


class KbEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: KbCategory
    title: str
    content: str
    updated_at: datetime
    has_embedding: bool = False


class KbEntryList(BaseModel):
    items: list[KbEntryOut]
    total: int
    page: int
    size: int


class KbEntryCreate(BaseModel):
    category: KbCategory = "institutional"
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=5000)


class KbEntryUpdate(BaseModel):
    category: Optional[KbCategory] = None
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, max_length=5000)
