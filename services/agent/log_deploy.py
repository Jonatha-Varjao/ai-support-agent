"""Driver script to log, register and deploy the agent on Databricks.

Run inside a Databricks notebook (or from a Databricks-connected shell):

    uv run python services/agent/log_deploy.py \
        --agent-path /Workspace/Users/<you>/agent.py \
        --catalog <catalog> --schema <schema> --model mission_agent \
        --endpoint mission-agent

Required environment variables:
  - DATABRICKS_HOST        (workspace URL, e.g. https://dbc-....cloud.databricks.com)
  - DATABRICKS_CLIENT_ID   (service principal application ID)
  - DATABRICKS_CLIENT_SECRET (service principal OAuth secret)
  - GEMINI_API_KEY         (secret passed to the deployed endpoint)
  - GEMINI_MODEL           (e.g. gemini-2.5-flash)
"""
from __future__ import annotations

import argparse
import os

import mlflow
from databricks import agents

# Secrets injected into the serving endpoint at deploy time.
DEPLOY_SECRETS = {"GEMINI_API_KEY", "GEMINI_MODEL"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log, register and deploy the Gemini inference agent.")
    parser.add_argument("--agent-path", required=True, help="Path to agent.py in the Databricks workspace.")
    parser.add_argument("--catalog", required=True, help="Unity Catalog catalog name.")
    parser.add_argument("--schema", required=True, help="Unity Catalog schema name.")
    parser.add_argument("--model", default="mission_agent", help="Unity Catalog model name.")
    parser.add_argument("--endpoint", default="mission-agent", help="Serving endpoint name.")
    parser.add_argument("--artifact-path", default="agent", help="MLflow artifact path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    mlflow.set_registry_uri("databricks-uc")

    input_example = {
        "input": [{"role": "user", "content": "O que é a Mission?"}],
        "custom_inputs": {
            "system_prompt": "Você é um agente de suporte da Mission Brasil.",
            "query": "O que é a Mission?",
        },
    }

    with mlflow.start_run():
        logged_info = mlflow.langchain.log_model(
            lc_model=args.agent_path,
            artifact_path=args.artifact_path,
            input_example=input_example,
            example_no_conversion=True,
        )
    print(f"MLflow Run: {logged_info.run_id}")
    print(f"Model URI: {logged_info.model_uri}")

    uc_model_name = f"{args.catalog}.{args.schema}.{args.model}"
    uc_info = mlflow.register_model(model_uri=logged_info.model_uri, name=uc_model_name)
    print(f"Registered: {uc_info.name} version {uc_info.version}")

    deployment = agents.deploy(
        uc_info.name,
        uc_info.version,
        endpoint_name=args.endpoint,
        secrets={name: os.environ[name] for name in DEPLOY_SECRETS if name in os.environ},
    )
    print(f"Deployed. Query endpoint: {deployment.query_endpoint}")


if __name__ == "__main__":
    main()
