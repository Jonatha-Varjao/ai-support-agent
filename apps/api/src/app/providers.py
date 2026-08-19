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
# Calls the deployed ResponsesAgent (services/agent/agent.py) via the
# official DatabricksOpenAI SDK (unified OAuth M2M auth). The agent only
# performs the LLM completion; RAG/prompt building stay in this backend.


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
    """LangChain chat model backed by a Databricks ResponsesAgent endpoint.

    Uses the official DatabricksOpenAI SDK (unified auth via DATABRICKS_*
    env vars). Falls back to raw httpx if the SDK is unavailable.
    """

    model: str = Field(default="")
    temperature: float = Field(default=0.7)

    @property
    def _llm_type(self) -> str:
        return "databricks-responses"

    def _get_client(self):
        try:
            from databricks_openai import DatabricksOpenAI
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()
            return DatabricksOpenAI(workspace_client=w)
        except Exception:
            return None

    # -- non-streaming ----------------------------------------------------

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        payload = _build_responses_payload(list(messages), self.temperature, stream=False)
        client = self._get_client()
        if client is not None:
            resp = client.responses.create(
                model=settings.databricks_endpoint_name,
                input=payload["input"],
                extra_body={"custom_inputs": payload["custom_inputs"]},
            )
            text = _extract_response_text(resp.to_dict() if hasattr(resp, "to_dict") else resp.model_dump())
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])
        # Fallback: manual httpx with OAuth token
        import httpx as _httpx
        import time as _time

        # Use SDK token cache if available
        from databricks.sdk import WorkspaceClient as _WC

        w = _WC()
        token = w.config.authenticate()["Authorization"].removeprefix("Bearer ").strip() if w.config.authenticate() else ""
        url = f"{settings.databricks_host}/serving-endpoints/{settings.databricks_endpoint_name}/invocations"
        headers = {"Authorization": f"Bearer {token}"}
        with _httpx.Client(timeout=180) as c:
            r = c.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        text = _extract_response_text(data)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        # Reuse sync path in thread to keep SDK usage simple
        import asyncio

        return await asyncio.to_thread(self._generate, messages, stop, run_manager, **kwargs)

    # -- streaming ----------------------------------------------------------

    def _stream(self, messages, stop=None, run_manager=None, **kwargs) -> Iterator[ChatGenerationChunk]:
        payload = _build_responses_payload(list(messages), self.temperature, stream=True)
        client = self._get_client()
        if client is not None:
            stream = client.responses.create(
                model=settings.databricks_endpoint_name,
                input=payload["input"],
                stream=True,
                extra_body={"custom_inputs": payload["custom_inputs"]},
            )
            for event in stream:
                d = event.to_dict() if hasattr(event, "to_dict") else event
                if d.get("type") == "response.output_text.delta":
                    yield ChatGenerationChunk(message=AIMessageChunk(content=d.get("delta", "")))
                elif d.get("type") == "response.output_item.done":
                    break
            return
        # Fallback streaming via httpx
        with httpx.Client(timeout=180) as c:
            from databricks.sdk import WorkspaceClient as _WC

            w = _WC()
            token = w.config.authenticate()["Authorization"].removeprefix("Bearer ").strip() if w.config.authenticate() else ""
            url = f"{settings.databricks_host}/serving-endpoints/{settings.databricks_endpoint_name}/invocations"
            headers = {"Authorization": f"Bearer {token}"}
            with c.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    if event.get("type") == "response.output_text.delta":
                        yield ChatGenerationChunk(message=AIMessageChunk(content=event.get("delta", "")))
                    elif event.get("type") == "response.output_item.done":
                        break

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        import asyncio

        # Delegate to sync stream in thread; preserves SSE contract
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run():
            try:
                for chunk in self._stream(messages, stop, run_manager, **kwargs):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        import threading

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item


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
