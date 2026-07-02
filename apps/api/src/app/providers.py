from __future__ import annotations

from langchain_community.chat_models.fake import FakeListChatModel
from langchain_core.embeddings import Embeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from .config import settings

# ── LLM provider ────────────────────────────────────────────────

DEFAULT_RESPONSE = "Desculpe, não encontrei informações suficientes para responder sua pergunta."


def get_llm(temperature: float = 0.7, mock_responses: list[str] | None = None):
    if not settings.gemini_api_key:
        return FakeListChatModel(responses=mock_responses or [DEFAULT_RESPONSE])
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
        convert_system_message_to_human=True,
    )


# ── Embedding provider ──────────────────────────────────────────

_embeddings: Embeddings | None = None


def get_embeddings() -> Embeddings:
    global _embeddings
    if _embeddings is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Set it in .env or docker-compose.yml.")
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=settings.gemini_api_key,
            output_dimensionality=settings.embedding_dim,
        )
    return _embeddings


async def warmup_embeddings() -> None:
    """Validate the Gemini API key by running one embedding."""
    embeddings = get_embeddings()
    await embeddings.aembed_query("warmup")
