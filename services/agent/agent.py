"""LLM inference agent for Databricks Model Serving.

A thin Gemini wrapper that brings Databricks observability (tracing,
Review App, inference tables) to the existing LLM inference step of the
AI Support Agent. All RAG retrieval, prompt building and caching remain
in the FastAPI backend; this agent only performs the LLM completion.

The agent contract uses `custom_inputs`:
  - system_prompt: full RAG system prompt built by the backend
  - query:         sanitized user question

Secrets are injected at deploy time via `agents.deploy(environment_vars=...)`:
  - GEMINI_API_KEY
  - GEMINI_MODEL
"""
from __future__ import annotations

import os
import uuid
from typing import Generator

import mlflow
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from mlflow.entities import SpanType
from mlflow.models import set_model
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)


class GeminiInferenceAgent(ResponsesAgent):
    """ResponsesAgent wrapper around a Gemini chat completion chain."""

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=os.environ["GEMINI_MODEL"],
            google_api_key=os.environ["GEMINI_API_KEY"],
            temperature=0.7,
            convert_system_message_to_human=True,
        )
        self.chain = self.llm | StrOutputParser()

    @mlflow.trace(span_type=SpanType.AGENT)
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        output_item = None
        for event in self.predict_stream(request):
            if event.type == "response.output_item.done":
                output_item = event.item
        return ResponsesAgentResponse(output=[output_item])

    @mlflow.trace(span_type=SpanType.AGENT)
    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        system_prompt = (request.custom_inputs or {}).get("system_prompt", "")
        query = (request.custom_inputs or {}).get("query", "")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query),
        ]
        item_id = str(uuid.uuid4())
        aggregated = ""
        for token in self.chain.stream(messages):
            aggregated += token
            yield ResponsesAgentStreamEvent(**self.create_text_delta(delta=token, item_id=item_id))
        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(text=aggregated, id=item_id),
        )


set_model(GeminiInferenceAgent())
