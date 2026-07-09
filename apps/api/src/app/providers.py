from __future__ import annotations

import logging
from functools import lru_cache

import mlflow
from langchain_community.chat_models.fake import FakeListChatModel
from langchain_core.embeddings import Embeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from .config import settings

logger = logging.getLogger(__name__)

# ── LLM provider ────────────────────────────────────────────────

DEFAULT_RESPONSE = "Desculpe, não encontrei informações suficientes para responder sua pergunta."


def get_llm(temperature: float = 0.7, mock_responses: list[str] | None = None):
    if not settings.gemini_api_key:
        return FakeListChatModel(responses=mock_responses or [DEFAULT_RESPONSE])
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
        convert_system_message_to_human=True,
    )


# ── Embedding provider ──────────────────────────────────────────


class _FakeEmbeddings(Embeddings):
    """Fallback for when no API key is configured. Returns zero vectors."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dim for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.dim

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set. Using fake embeddings (zero vectors).")
        return _FakeEmbeddings(dim=settings.embedding_dim)
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=settings.gemini_api_key,
        output_dimensionality=settings.embedding_dim,
    )


@mlflow.trace(span_type="EMBEDDING")
async def warmup_embeddings() -> None:
    """Validate the Gemini API key by running one embedding."""
    embeddings = get_embeddings()
    if isinstance(embeddings, _FakeEmbeddings):
        logger.info("Skipping embedding warmup — fake embeddings in use.")
        return
    try:
        await embeddings.aembed_query("warmup")
    except Exception:
        logger.warning("Embedding warmup failed; will retry on demand.", exc_info=True)
