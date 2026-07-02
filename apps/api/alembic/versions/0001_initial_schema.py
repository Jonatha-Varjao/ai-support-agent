"""initial schema: create all tables with vector(384) + indexes

Revision ID: 0001
Revises:
Create Date: 2026-07-01

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── users ──────────────────────────────────────────────────────
    op.create_table("users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), server_default="user", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="users_email_ux"),
    )

    # ── threads ────────────────────────────────────────────────────
    op.create_table("threads",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), server_default="", nullable=False),
        sa.Column("archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("threads_user_id_ix", "threads", ["user_id"])

    # ── messages ───────────────────────────────────────────────────
    op.create_table("messages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'tool')", name="ck_messages_role"),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("messages_thread_id_ix", "messages", ["thread_id"])
    op.create_index("messages_created_at_ix", "messages", ["created_at"])

    # ── kb_entries ─────────────────────────────────────────────────
    op.create_table("kb_entries",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("fts", postgresql.TSVECTOR(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("category IN ('product', 'service', 'flow', 'institutional', 'faq')", name="ck_kb_category"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("kb_entries_fts_gin", "kb_entries", ["fts"], postgresql_using="gin")
    op.create_index("kb_entries_category_ix", "kb_entries", ["category"])
    op.create_index("kb_entries_embedding_null_ix", "kb_entries", ["embedding"], postgresql_where=sa.text("embedding IS NULL"))
    op.execute("CREATE INDEX kb_entries_embedding_hnsw ON kb_entries USING hnsw (embedding vector_cosine_ops)")

    # ── unanswered_questions ───────────────────────────────────────
    op.create_table("unanswered_questions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("top_sim", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(32), server_default="no_context", nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("reason IN ('no_context', 'injection')", name="ck_unanswered_reason"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("unresolved_ix", "unanswered_questions", ["created_at"], postgresql_where=sa.text("resolved = false"))

    # ── human_requests ─────────────────────────────────────────────
    op.create_table("human_requests",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(16), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('open', 'contacted', 'closed')", name="ck_human_status"),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("open_handoffs_ix", "human_requests", ["created_at"], postgresql_where=sa.text("status = 'open'"))

    # ── response_cache ─────────────────────────────────────────────
    op.create_table("response_cache",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("query_embedding", Vector(384), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("hits", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("CREATE INDEX response_cache_q_hnsw ON response_cache USING hnsw (query_embedding vector_cosine_ops)")
    op.create_index("response_cache_expires_at_ix", "response_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("response_cache_expires_at_ix", table_name="response_cache")
    op.execute("DROP INDEX IF EXISTS response_cache_q_hnsw")
    op.drop_index("open_handoffs_ix", table_name="human_requests")
    op.drop_index("unresolved_ix", table_name="unanswered_questions")
    op.execute("DROP INDEX IF EXISTS kb_entries_embedding_hnsw")
    op.drop_index("kb_entries_embedding_null_ix", table_name="kb_entries")
    op.drop_index("kb_entries_category_ix", table_name="kb_entries")
    op.drop_index("kb_entries_fts_gin", table_name="kb_entries")
    op.drop_index("messages_created_at_ix", table_name="messages")
    op.drop_index("messages_thread_id_ix", table_name="messages")
    op.drop_index("threads_user_id_ix", table_name="threads")
    op.drop_table("response_cache")
    op.drop_table("human_requests")
    op.drop_table("unanswered_questions")
    op.drop_table("kb_entries")
    op.drop_table("messages")
    op.drop_table("threads")
    op.drop_table("users")
