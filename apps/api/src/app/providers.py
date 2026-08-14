from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from typing import Any, Iterator

import httpx
import mlflow
from langchain_community.chat_models.fake import FakeListChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from pydantic import Field

from .config import settings

logger = logging.getLogger(__name__)

# ── LLM provider ────────────────────────────────────────────────

DEFAULT_RESPONSE = "Desculpe, não encontrei informações suficientes para responder sua pergunta."


def get_llm(temperature: float = 0.7, mock_responses: list[str] | None = None):
    if settings.llm_provider == "databricks":
        if not settings.databricks_host or not settings.databricks_endpoint_name:
            raise RuntimeError("DATABRICKS_* env vars are not configured. Set them in .env or docker-compose.yml.")
        return DatabricksResponsesChatModel(temperature=temperature)
    if not settings.gemini_api_key:
        return FakeListChatModel(responses=mock_responses or [DEFAULT_RESPONSE])
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
        convert_system_message_to_human=True,
    )


# ── Databricks serving endpoint provider ────────────────────────
# Calls the deployed ResponsesAgent (services/agent/agent.py) using
# OAuth M2M client-credentials auth. The agent only performs the LLM
# completion; RAG/prompt building stay in this backend.

_token_cache: dict[str, Any] = {"token": None, "exp": 0.0}


def _databricks_access_token() -> str:
    """Return a valid OAuth M2M token, fetching/refreshing as needed."""
    if _token_cache["token"] and _token_cache["exp"] > time.time() + 60:
        return _token_cache["token"]
    resp = httpx.post(
        f"{settings.databricks_host}/oidc/v1/token",
        data={"grant_type": "client_credentials", "scope": "all-apis"},
        auth=(settings.databricks_client_id, settings.databricks_client_secret),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["exp"] = time.time() + int(data.get("expires_in", 3600))
    return _token_cache["token"]


def _responses_endpoint_url() -> str:
    return f"{settings.databricks_host}/serving-endpoints/{settings.databricks_endpoint_name}/responses"


def _build_responses_payload(messages: list[BaseMessage], temperature: float, stream: bool) -> dict:
    """Convert LangChain messages to the ResponsesAgent contract.

    Phase 1: the agent receives the full system prompt plus the conversation
    (history + current query) via custom_inputs. Tool calling is not
    forwarded yet — the serving endpoint is a thin LLM proxy.
    """
    system_parts = [m.content for m in messages if getattr(m, "type", "") == "system"]
    others = [m for m in messages if getattr(m, "type", "") != "system"]

    history_lines: list[str] = []
    for m in others[:-1]:
        role = "user" if m.type == "human" else "assistant"
        history_lines.append(f"{role}: {m.content}")
    query = others[-1].content if others else ""

    full_query = query
    if history_lines:
        full_query = "[Histórico]\n" + "\n".join(history_lines) + "\n\n[Pergunta]\n" + query

    return {
        "input": [{"role": "user", "content": full_query}],
        "custom_inputs": {"system_prompt": "\n".join(system_parts), "query": full_query},
        "temperature": temperature,
        "stream": stream,
    }


def _extract_response_text(data: dict) -> str:
    parts: list[str] = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    parts.append(content.get("text", ""))
    return "".join(parts)


class DatabricksResponsesChatModel(BaseChatModel):
    """LangChain chat model backed by a Databricks ResponsesAgent endpoint."""

    model: str = Field(default="")
    temperature: float = Field(default=0.7)

    @property
    def _llm_type(self) -> str:
        return "databricks-responses"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {_databricks_access_token()}"}

    # -- non-streaming ----------------------------------------------------

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        payload = _build_responses_payload(list(messages), self.temperature, stream=False)
        with httpx.Client(timeout=180) as client:
            resp = client.post(_responses_endpoint_url(), json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        text = _extract_response_text(data)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        payload = _build_responses_payload(list(messages), self.temperature, stream=False)
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(_responses_endpoint_url(), json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        text = _extract_response_text(data)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    # -- streaming ----------------------------------------------------------

    def _stream(self, messages, stop=None, run_manager=None, **kwargs) -> Iterator[ChatGenerationChunk]:
        payload = _build_responses_payload(list(messages), self.temperature, stream=True)
        with httpx.Client(timeout=180) as client:
            with client.stream("POST", _responses_endpoint_url(), json=payload, headers=self._headers()) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    if event.get("type") == "response.output_text.delta":
                        delta = event.get("delta", "")
                        yield ChatGenerationChunk(message=AIMessageChunk(content=delta))
                    elif event.get("type") == "response.output_item.done":
                        break

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        payload = _build_responses_payload(list(messages), self.temperature, stream=True)
        async with httpx.AsyncClient(timeout=180) as client:
            async with client.stream("POST", _responses_endpoint_url(), json=payload, headers=self._headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    if event.get("type") == "response.output_text.delta":
                        delta = event.get("delta", "")
                        yield ChatGenerationChunk(message=AIMessageChunk(content=delta))
                    elif event.get("type") == "response.output_item.done":
                        break


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
