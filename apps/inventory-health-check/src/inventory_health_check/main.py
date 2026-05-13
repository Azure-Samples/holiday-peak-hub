"""Inventory health check service."""

import os

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from inventory_health_check.agents import InventoryHealthAgent, register_mcp_tools
from inventory_health_check.event_handlers import build_event_handlers

SERVICE_NAME = "inventory-health-check"
# Pilot service for the ADR-005 (2026-05-10) Mandatory MAF Invocation Policy:
# wire SLM/LLM targets via DirectModelInvoker (in-process MAF Agent +
# FoundryChatClient over Responses API) instead of portal-managed Foundry
# Prompt Agents. No parallel runtime — this opts the existing entry point in.
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=InventoryHealthAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "health-check-group"),
        EventHubSubscription("inventory-events", "health-check-group"),
    ],
    handlers=build_event_handlers(),
    use_direct_model=True,
)

# Foundry Hosted Agent (preview) — single-process mount that exposes the
# Responses-protocol surface (``/v1/responses``) on the SAME FastAPI app.
# Single uvicorn process, single port, no second runtime — the dual-runtime
# guardrail in ADR-005 (2026-05-10) targets the multi-process / multi-port
# shape and is preserved by this mount pattern. Direct routes registered
# above (``/health``, ``/ready``, ``/mcp/*``) win because Starlette walks
# routes in registration order.
#
# Toggleable: set HOLIDAY_PEAK_FOUNDRY_HOSTED=0 to skip mounting (for
# environments where ``agent-framework-foundry-hosting`` is not installed
# or where the operator wants to roll back the pilot without redeploying).
if os.getenv("HOLIDAY_PEAK_FOUNDRY_HOSTED", "1") not in ("0", "false", "False"):
    try:
        app.state.agent.serve_hosted(app)
    except ImportError:
        # The optional SDK is not present in this environment — log and
        # continue. Service still serves /health, /mcp/*, /ready normally.
        import logging

        logging.getLogger(SERVICE_NAME).warning(
            "foundry_hosted_mount_skipped reason=sdk_missing "
            "(install agent-framework-foundry-hosting to enable portal indexing)"
        )
