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
    └── DatabricksOpenAI (unified OAuth) ────┘
         ↓ responses.create(model=endpoint, extra_body={custom_inputs})
    Databricks Model Serving (ResponsesAgent — Gemini)
         ├── Managed MLflow traces (auto, UC if configured)
         ├── Review App (feedback)
         └── AI Gateway inference tables
```

## What moved to Databricks (Phase 1)

| Concern | `main` (handcrafted) | `main-databricks` |
|---|---|---|
| LLM inference | Gemini API directly (`langchain-google-genai`) | Databricks `DatabricksOpenAI` → `responses.create(model=endpoint)` |
| Tracing | Self-hosted MLflow + `@mlflow.trace` | Dual-write: self-hosted **and** Databricks UC-managed (OTel Delta) |
| Auth | `GEMINI_API_KEY` | `databricks-sdk` unified auth (`DATABRICKS_HOST/CLIENT_ID/CLIENT_SECRET`) |
| RAG / cache / DB | Self-hosted | Self-hosted (unchanged) |
| Evaluation / feedback | Manual (future) | `mlflow.genai.evaluate()` + Review App + Lakehouse Monitoring |

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
(`DatabricksResponsesChatModel` via `DatabricksOpenAI`) converts to the exact
same SSE `{"type":"token",...}` frames — the frontend is unchanged on both branches.

Backend auth uses `databricks-sdk` unified OAuth (env vars `DATABRICKS_HOST/CLIENT_ID/CLIENT_SECRET`);
no manual `/oidc/v1/token` handling — the SDK auto-refreshes the 1h token.

**Chat layer:** `apps/api/src/app/chat.py:716` branches on `llm_provider`:
- `gemini` → `llm.bind_tools(...)` + `ainvoke`/`astream` (tool-aware)
- `databricks` → direct `llm.astream(messages)` (Phase 1: thin LLM proxy, no tool forwarding)

## Setup (manual, requires a Databricks workspace)

### 1. Prerequisites

- Databricks workspace (Free Edition for notebooks; enterprise for serving endpoints)
- Service principal + OAuth secret (Account Console → Identity → Service Principals → Secrets, 730d)

### 2. Deploy the agent

In a Databricks notebook (or connected shell):

```bash
export GEMINI_API_KEY=...      # or use Databricks secrets scope
export GEMINI_MODEL=gemini-3.1-flash-lite
export DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
export DATABRICKS_CLIENT_ID=<service-principal-client-id>
export DATABRICKS_CLIENT_SECRET=<oauth-secret>

# Code-based logging — ResponsesAgent via mlflow.pyfunc (not langchain)
uv run python services/agent/log_deploy.py \
  --agent-path /Workspace/Users/<you>/agent.py \
  --catalog main --schema mission \
  --model mission_agent --endpoint mission-agent
# Internally: mlflow.pyfunc.log_model(python_model=..., name="agent")
#            + mlflow.register_model → Unity Catalog
#            + agents.deploy(..., environment_vars={GEMINI_API_KEY: "{{secrets/mission/gemini-api-key}}"})
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

- **Good:** full control, no vendor lock-in, zero marginal cost, data stays local, `@mlflow.trace` + LangChain autolog are explicit.
- **Odds:** you build evaluation, feedback, monitoring, prompt versioning yourself; ops burden (Redis, Postgres, MLflow server).

### Databricks (`main-databricks`)

- **Good:** one `deploy()` gives serving endpoint + auto tracing + Review App +
  inference tables + Lakehouse Monitoring. Zero-downtime deployments, auto-scaling, Unity Catalog governance.
- **Odds:** vendor lock-in, cost (endpoint uptime + tokens), data leaves your infra, RAG/cache orchestration must be re-architected into Databricks services later (Vector Search, etc.).

### Alternative not chosen for POC: Foundation Model API

Enable `databricks-meta-llama-3-3-70b-instruct` in Serving → no custom agent code. Cheapest for prototype, fixed models, less control. Documented here for comparison — see `docs/databricks-serving-quickstart.md`.

## Observability: Databricks as a stack

Phase 1 keeps **side-by-side** tracing: self-hosted MLflow traces FastAPI orchestration, Databricks managed MLflow traces the serving endpoint.
Phase M2 moves to **UC-managed traces** (OTel Delta tables, 100k → unlimited, SQL + Genie queryable) plus Prompt Registry, `mlflow.genai.evaluate()`, and Review App.
See `docs/databricks-observability.md` (M2) and `docs/plans/databricks-roadmap.md` for the full lakehouse + evaluation roadmap.

## Known limitations (Phase 1)

- Tool calling (web_fetch/web_search) is not forwarded to the Databricks agent yet — serving endpoint is a thin LLM proxy (see `chat.py` branch). Tool orchestration is a later phase.
- The ResponsesAgent endpoint must be reachable from the backend (public endpoint or Private Link + network policy).
- Free Edition does not support agent serving endpoints; use a paid/enterprise workspace for the deployment step.
