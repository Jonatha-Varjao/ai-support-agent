# Databricks Serving Quickstart — LLM Provider POC

> **Goal:** Create the AI/ML serving endpoint so the app (`LLM_PROVIDER=databricks`) can use it. Then verify observability lives in Databricks.

## Prerequisites

- Databricks workspace (Free Edition for notebooks, **enterprise for serving**)
- Service principal + OAuth M2M secret: Account Console → Identity → Service Principals → Secrets → Generate (730d)
- Grant: workspace access + `main.mission.*` Unity Catalog + serving endpoint `CAN_MANAGE`
- Local: `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` in env

## 1. Upload Agent Code

Databricks Workspace → Workspace Files → `/Workspace/Users/<you>/mission-agent/` → upload:
- `services/agent/agent.py`
- `services/agent/config.yml`

Create secret scope for Gemini:
```
databricks secrets create-scope mission
databricks secrets put-secret mission gemini-api-key --string-value $GEMINI_API_KEY
```

## 2. Log the Agent (Databricks notebook)

```python
import mlflow
mlflow.set_registry_uri("databricks-uc")

with mlflow.start_run():
  info = mlflow.pyfunc.log_model(
    python_model="/Workspace/Users/<you>/mission-agent/agent.py",
    name="agent",
    input_example={
      "input": [{"role": "user", "content": "O que é a Mission?"}],
      "custom_inputs": {"system_prompt": "Você é um agente ...", "query": "O que é a Mission?"}
    },
  )
print(info.model_uri)  # runs:/<id>/agent
```

## 3. Register in Unity Catalog

```python
uc_info = mlflow.register_model(model_uri=info.model_uri, name="main.mission.mission_agent")
# version 1
```

## 4. Deploy

```python
from databricks import agents
dep = agents.deploy(
  "main.mission.mission_agent", 1,
  endpoint_name="mission-agent",
  environment_vars={
    "GEMINI_API_KEY": "{{secrets/mission/gemini-api-key}}",
    "GEMINI_MODEL": "gemini-3.1-flash-lite"
  },
)
print(dep.query_endpoint)
# https://<host>/serving-endpoints/mission-agent/invocations
```

Databricks auto-provisions: endpoint + MLflow traces + Review App + inference tables.

## 5. Wire the App

```bash
# .env or docker-compose
LLM_PROVIDER=databricks
DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
DATABRICKS_CLIENT_ID=<app-id>
DATABRICKS_CLIENT_SECRET=<oauth-secret>
DATABRICKS_ENDPOINT_NAME=mission-agent
```

Backend uses `DatabricksOpenAI` + unified OAuth (auto-refresh, no manual `/oidc/v1/token`).

## 6. Verify

```bash
# Non-streaming
curl -X POST https://$DATABRICKS_HOST/serving-endpoints/mission-agent/invocations \
  -H "Authorization: Bearer $(databricks auth token --host $DATABRICKS_HOST)" \
  -H "Content-Type: application/json" \
  -d '{"input":[{"role":"user","content":"O que é a Mission?"}],"custom_inputs":{"system_prompt":"...","query":"O que é a Mission?"}}'

# Streaming (via app, same SSE)
LLM_PROVIDER=databricks uv run python -m apps.api  # then chat in UI, check SSE frames unchanged
```

Check traces:
- **Self-hosted:** http://localhost:5000 → experiment `ai-support-agent-v2`
- **Databricks:** Workspace → Experiments → `main.mission.mission_agent` + Serving → Inference tables `system.ai.*`

## 7. Rollback

```bash
LLM_PROVIDER=gemini  # no code change, instant
```

## Alternative: Foundation Model API (no custom deploy)

Enable `databricks-meta-llama-3-3-70b-instruct` in Serving → Foundation Model APIs. Point `DATABRICKS_ENDPOINT_NAME` to it. No `agent.py` needed. Tradeoff: pay-per-token (Databricks), fixed models, less control — best for fast prototype (see `docs/databricks-approach.md` comparison).

## Troubleshooting

- `403 Invalid Host header` → ensure `DATABRICKS_HOST` matches workspace URL, service principal has `CAN_MANAGE` on endpoint.
- `401` → regenerate OAuth secret, check `DATABRICKS_CLIENT_SECRET` not expired.
- `404 endpoint` → `agents.get_deployments("main.mission.mission_agent")` to check status.
- No trace → `mlflow.set_tracking_uri("databricks")` vs self-hosted; check `MLFLOW_TRACKING_URI` env.
