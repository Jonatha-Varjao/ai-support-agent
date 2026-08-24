# Databricks Roadmap — AI Support Agent

> **Purpose (steering):** Learn the Databricks Lakehouse + Agent ecosystem end-to-end via this app. Every milestone must teach one platform concept and leave both branches shippable for side-by-side comparison (`main` = handcrafted MLOps, `main-databricks` = Databricks-managed). Single source of truth for future agentic sessions.

## Decisions Locked

| Decision | Choice | Why |
|---|---|---|
| Worktree | `.worktrees/main-databricks` (`main-databricks` branch, gitignored) | Parallel development, no sibling folder |
| LLM cheapest | Gemini API (called from inside the serving agent) | Cost vs. Databricks pay-per-token; Foundation Model API kept as documented alternative |
| Serving contract | `custom_inputs={system_prompt, query}` + `input=[{role:user}]` | Backend keeps ALL RAG; Databricks agent is thin LLM proxy; SSE stays `{"type":"token",...}` |
| Streaming | Same SSE frames on both branches | Frontend unchanged |
| Auth POC | OAuth M2M (service principal client credentials) | Backend-to-backend, 1h token auto-refresh via `databricks-sdk` unified auth |
| Observability short-term | Dual-write (Phase M2) or side-by-side now | Self-hosted traces stay; Databricks traces come from endpoint |
| Observability long-term | UC-managed traces (Delta OTel tables, unlimited) | `llms.txt` -> `/mlflow3/genai/tracing/` |
| Data lake | Medallion `mission_raw` → `mission_curated` → `mission.served.agent_kpis` | `UC_SYNC_MODE=snapshot|incremental` env toggle |
| Plans artefact | `docs/plans/databricks-roadmap.md` | Discoverable by `glob docs/**` |

## Architecture

```
Frontend (React) — identical SSE
  ↓
FastAPI (.worktrees/main-databricks)
  ├── RAG: PostgreSQL 17 + pgvector + FTS hybrid (vector_weight 0.85)  [stays]
  ├── Cache: Redis/RedisVL (semantic)                                  [stays]
  ├── Handoff: classification                                           [stays]
  ├── MLflow self-hosted http://mlflow:5000 (traces: RAG/cache/handoff) [stays]
  └── Databricks provider (LLM_PROVIDER=databricks)
       ↓ OAuth M2M → POST {DATABRICKS_HOST}/serving-endpoints/{ENDPOINT}/invocations
       Databricks Model Serving — ResponsesAgent (Gemini)
         ├── Managed MLflow (auto traces, Review App, inference tables)
         └── Unity Catalog (model registry)

Analytics (later): PostgreSQL → Delta UC (`sync_to_uc.py`) → Dashboards/Genie
```

## Key File Map

| File | Role | Status |
|---|---|---|
| `services/agent/agent.py:1` | `GeminiInferenceAgent(ResponsesAgent)` `predict`/`predict_stream` | Exists, needs `@mlflow.trace` fix |
| `services/agent/log_deploy.py:53` | `mlflow.pyfunc.log_model` + UC register + `agents.deploy(environment_vars=)` | Exists, needs flavor/arg fix |
| `services/agent/config.yml` | `ModelConfig` | Exists |
| `services/analytics/sync_to_uc.py` | PG → UC Delta, `MERGE` | Exists, needs typed DDL fix |
| `apps/api/src/app/providers.py:28` | `get_llm()` router + `DatabricksResponsesChatModel` | Exists, needs `DatabricksOpenAI` + no manual httpx token |
| `apps/api/src/app/chat.py:716` | `bind_tools` + `ainvoke`/`astream` | Needs provider-aware branch |
| `apps/api/src/app/config.py:39` | `llm_provider`, 4x `databricks_*` | Done |
| `infra/docker-compose.yml:82` | Databricks env passthrough | Done |

## Milestones — Sequential (M1 now, M2→M3 next)

### M1 — Serving Endpoint (POC) — *this execution*
- **Goal:** `LLM_PROVIDER=databricks` streams same SSE as `gemini`.
- **Concepts:** ResponsesAgent, Model Serving, OAuth M2M, Unity Catalog model.
- **Fixes:** (1) `chat.py` branch to skip `bind_tools` when databricks, single `astream`. (2) `providers.py` → `DatabricksOpenAI(workspace_client=WorkspaceClient())` instead of manual `httpx`. (3) `log_deploy.py` → `mlflow.pyfunc.log_model(name="agent")` + `environment_vars`.
- **Verify:** `curl` + chat SSE + Databricks trace appears.
- **Docs:** `docs/databricks-serving-quickstart.md` + polish `docs/databricks-approach.md` comparison table.

### M2 — Observability → Evaluation Loop
- **Goal:** Understand MLflow 3 on Databricks as evaluation platform.
- **Concepts:** UC-managed traces (OTel Delta), Prompt Registry, `mlflow.genai.evaluate()` with judge on 20-row dataset (`unanswered_questions`+KB), Review App (`agents.enable_trace_reviews`), Lakehouse Monitoring, inference tables.
- **Docs:** `docs/databricks-observability.md`.

### M3 — Data Lake Path
- **Goal:** Understand lakehouse via this app's data.
- **Concepts:** Delta CDF/time travel/`OPTIMIZE`/`VACUUM`, Unity Catalog catalog/schema/volume, Genie, AI/BI dashboards, System Tables (`system.billing`, `system.access`).
- **Deliverable:** Proper typed medallion, Genie space over UC tables.

### M4 — Expansion (later)
- AI Search vs pgvector benchmark, AI Gateway cost routing, Lakebase Postgres note.

## Concise Endpoint Steps (from llms.txt)

> Anchors: `/agents/custom-agents/model-serving/author-agent-model-serving`, `/agents/custom-agents/model-serving/log-agent`, `/machine-learning/model-serving/create-manage-serving-endpoints`, `/agents/custom-agents/query-agent`

1. Prereqs: workspace + service principal + OAuth secret (730d) + grant workspace/UC/serving perms.
2. Secret scope: `databricks secrets create-scope mission` + put `gemini-api-key`.
3. Upload `services/agent/agent.py` → Workspace Files.
4. Log: `mlflow.pyfunc.log_model(python_model="agent.py", name="agent", input_example=RESPONSES_AGENT_INPUT_EXAMPLE)` + `mlflow.models.set_model(agent)`.
5. Register: `mlflow.register_model(model_uri, "main.mission.mission_agent")`.
6. Deploy: `agents.deploy(name, version, endpoint_name="mission-agent", environment_vars={"GEMINI_API_KEY":"{{secrets/mission/gemini-api-key}}","GEMINI_MODEL":"gemini-3.1-flash-lite"})`.
7. Wire: `LLM_PROVIDER=databricks` + 4 `DATABRICKS_*` envs → `DatabricksOpenAI.responses.create(model=endpoint, extra_body={"custom_inputs":...}, stream=True)`.
8. Verify: one non-stream + one stream call, check SSE + trace.

## Alternatives Discussed (for docs)

| | Custom Agent (Gemini wrapper) — **chosen** | Foundation Model API |
|---|---|---|
| Setup | Agent code + UC + deploy | Enable `databricks-meta-llama-3-3-70b-instruct` (no code) |
| Cost | Gemini API + endpoint uptime | Pay-per-token (DBRX/Llama) |
| Control | Full prompt logic | Fixed models |
| When | Custom production workflows | Fast prototype |

## Open Decisions Log

| Date | Decision | Notes |
|---|---|---|
| 2026-01-XX | Dual-write toggled vs always-on | Use `MLFLOW_DUAL_WRITE=true` env toggle (future) |
| 2026-01-XX | Worktree inside repo | `.worktrees/main-databricks` gitignored |

## References

- `https://docs.databricks.com/llms.txt`
- MLflow Tracing: `/mlflow3/genai/tracing/`
- MLflow Prompt Registry: `/mlflow3/genai/prompt-version-mgmt/prompt-registry/`
- Evaluate: `/mlflow3/genai/eval-monitor/`
- ResponsesAgent: `https://mlflow.org/docs/latest/genai/serving/responses-agent/`
