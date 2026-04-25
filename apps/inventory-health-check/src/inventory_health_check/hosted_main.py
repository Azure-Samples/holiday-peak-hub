"""Foundry hosted agent entry point for the Inventory Health Check agent.

Wraps the InventoryHealthAgent with the Agent Framework hosting adapter,
exposing it via the Foundry Responses API on port 8088.

This is an ADDITIONAL entry point — the existing FastAPI service (main.py)
remains the default for backward-compatible AKS deployment.
"""

import logging
import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

load_dotenv(override=False)

logger = logging.getLogger(__name__)

if not os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    logger.warning(
        "APPLICATIONINSIGHTS_CONNECTION_STRING not set — traces will not be sent to "
        "Application Insights. Set it to enable local telemetry. "
        "(This variable is auto-injected in hosted Foundry containers.)"
    )


def _load_instructions() -> str:
    """Load agent instructions from the prompts directory."""
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")
    instructions_path = os.path.join(prompts_dir, "instructions.md")
    if os.path.exists(instructions_path):
        with open(instructions_path, encoding="utf-8") as f:
            return f.read()
    # Fallback for containerized layout
    container_path = os.path.join(os.getcwd(), "prompts", "instructions.md")
    if os.path.exists(container_path):
        with open(container_path, encoding="utf-8") as f:
            return f.read()
    return (
        "You are the inventory health check agent for Holiday Peak Hub. "
        "Assess inventory integrity and operational risk signals."
    )


def main() -> None:
    """Create and run the Foundry hosted agent."""
    project_endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not project_endpoint:
        raise EnvironmentError(
            "PROJECT_ENDPOINT environment variable is not set. "
            "Set it to your Foundry project endpoint."
        )

    model_deployment = os.environ.get(
        "MODEL_DEPLOYMENT_NAME_FAST",
        os.environ.get("MODEL_DEPLOYMENT_NAME_RICH", "gpt-5-nano"),
    )

    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model_deployment,
        credential=DefaultAzureCredential(),
    )

    instructions = _load_instructions()

    agent = Agent(
        client=client,
        instructions=instructions,
        name="inventory-health-check",
        default_options={"store": False},
    )

    # Bridge our PROJECT_ENDPOINT to FOUNDRY_PROJECT_ENDPOINT so
    # ResponsesHostServer's FoundryStorageSettings can resolve it.
    os.environ.setdefault("FOUNDRY_PROJECT_ENDPOINT", project_endpoint)
    os.environ.setdefault("FOUNDRY_AGENT_NAME", "inventory-health-check-hosted")

    async def _liveness(request: Request) -> Response:
        return Response(b'{"status":"healthy"}', media_type="application/json")

    liveness_route = Route("/liveness", _liveness, methods=["GET"])

    server = ResponsesHostServer(agent, routes=[liveness_route])
    server.run()


if __name__ == "__main__":
    main()
