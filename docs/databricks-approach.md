# Databricks Approach — Observability & LLM Inference via Databricks

This document describes the `main-databricks` branch: the same AI Support Agent
app, but with the **LLM inference step** served by a Databricks Model Serving
endpoint instead of calling the Gemini API directly. The goal is to study the
tradeoffs between a fully handcrafted MLOps stack (`main` branch) and a managed
platform (Databricks) — side by side, with the same questions.

## Architecture

```
Frontend (React SPA)
    ↓ SSE (identical on both branches)
FastAPI backend ──────────────────────────────┐
    ├── PostgreSQL + pgvector (RAG)          │
    ├── Redis (semantic cache)               │
    ├── Handoff classification               │
    ├── Self-hosted MLflow (traces)          │   ← side-by-side observability
    │                                        │
    └── OAuth M2M (client credentials) ──────┘
         ↓ POST /serving-endpoints/<name>/responses
    Databricks Model Serving (ResponsesAgent)
         ├── Managed MLflow traces (auto)
         ├── Review App (feedback)
         └── AI Gateway inference tables
```

## What moved to Databricks (Phase 1)

| Concern | `main` (handcrafted) | `main-databricks` |
|---|---|---|
| LLM inference | Gemini API directly (`langchain-google-genai`) | Databricks ResponsesAgent serving endpoint |
| Tracing | Self-hosted MLflow + `@mlflow.trace` | Self-hosted MLflow **and** Databricks managed MLflow |
| Auth | `GEMINI_API_KEY` | Service principal OAuth M2M (client credentials) |
| RAG / cache / DB | Self-hosted | Self-hosted (unchanged) |
| Evaluation / feedback | Manual (future) | Review App, inference tables (Databricks) |

## Repo layout (this branch)

```
services/
├── agent/                        # runs inside Databricks
│   ├── agent.py                  # ResponsesAgent wrapper (Gemini LLM)
│   ├── config.yml                # ModelConfig
│   └── log_deploy.py             # log → Unity Catalog → deploy driver
└── analytics/
    └── sync_to_uc.py             # PostgreSQL → Unity Catalog Delta sync
```

## Agent contract

The deployed agent is a thin LLM proxy. The backend keeps ALL RAG logic and
sends the final prompt via `custom_inputs`:

```json
{
  "input": [{"role": "user", "content": "<query>"}],
  "custom_inputs": {
    "system_prompt": "<RAG system prompt built by the backend>",
    "query": "<sanitized user question + history>"
  },
  "stream": true
}
```

The agent streams `response.output_text.delta` events, which the backend
converts to the exact same SSE `{"type":"token",...}` frames — the frontend is
unchanged on both branches.

## Setup (manual, requires a Databricks workspace)

### 1. Prerequisites

- Databricks workspace (Free Edition for notebooks; enterprise for serving endpoints)
- Service principal + OAuth secret (see Databricks docs: OAuth M2M)

### 2. Deploy the agent

In a Databricks notebook (or connected shell):

```bash
export GEMINI_API_KEY=...      # or use Databricks secrets
export GEMINI_MODEL=gemini-3.1-flash-lite
export DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
export DATABRICKS_CLIENT_ID=<service-principal-client-id>
export DATABRICKS_CLIENT_SECRET=<oauth-secret>

uv run python services/agent/log_deploy.py \
  --agent-path /Workspace/Users/<you>/agent.py \
  --catalog main --schema mission \
  --model mission_agent --endpoint mission-agent
```

### 3. Configure the backend

```bash
# .env (or docker-compose environment)
LLM_PROVIDER=databricks
DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
DATABRICKS_CLIENT_ID=<service-principal-client-id>
DATABRICKS_CLIENT_SECRET=<oauth-secret>
DATABRICKS_ENDPOINT_NAME=mission-agent
```

Switch back with `LLM_PROVIDER=gemini` — no code changes needed.

### 4. Unity Catalog analytics (optional)

```bash
export DATABASE_URL=postgresql+psycopg://aiagent:aiagent@localhost:5432/aiagent
export DATABRICKS_UC_CATALOG=main
export DATABRICKS_UC_SCHEMA=mission
export UC_SYNC_MODE=snapshot     # or incremental

uv run python services/analytics/sync_to_uc.py
```

Syncs `threads`, `messages`, `unanswered_questions`, `human_requests`,
`kb_entries` into Unity Catalog Delta tables for dashboards/SQL analytics.

## Tradeoffs (study notes)

### Handcrafted (`main`)

- **Good:** full control, no vendor lock-in, zero marginal cost, data stays local.
- **Odds:** you build evaluation, feedback, monitoring, prompt versioning yourself.

### Databricks (`main-databricks`)

- **Good:** one `deploy()` gives serving endpoint + auto tracing + Review App +
  inference tables + production monitoring. Zero-downtime deployments, auto-scaling.
- **Odds:** vendor lock-in, cost, data leaves your infra, RAG/cache orchestration
  must be re-architected into Databricks services later (Vector Search, etc.).

## Known limitations (Phase 1)

- Tool calling (web_fetch/web_search) is not forwarded to the Databricks agent
  yet — the serving endpoint is a thin LLM proxy. Tool orchestration is a later phase.
- The ResponsesAgent endpoint must be reachable from the backend (public endpoint
  or Private Link + network policy).
- Free Edition does not support agent serving endpoints; use a paid/enterprise
  workspace for the deployment step.
