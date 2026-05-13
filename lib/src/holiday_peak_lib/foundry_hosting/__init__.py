"""Foundry V3 Hosted Agents — manifest schema and SDK-based deployment.

This subpackage owns the operational surface for registering containerised
agents with Azure AI Foundry Agent Service (hosted, V3, public preview).

Responsibilities split:

* :mod:`holiday_peak_lib.agents.hosted` — the in-process mount that exposes the
  ``/responses`` protocol surface on an existing FastAPI app.
* :mod:`holiday_peak_lib.foundry_hosting.manifest` — Pydantic model for the
  per-service ``agent.yaml`` declaration (``template.kind: hosted``).
* :mod:`holiday_peak_lib.foundry_hosting.deploy` — small async wrapper around
  ``project.agents.create_version()`` that polls until the version reports
  ``active`` (or raises with the platform error).

The split keeps the optional ``agent-framework-foundry-hosting`` SDK out of
this subpackage entirely: deployment uses ``azure-ai-projects`` which the
service runtime already depends on. Services that opt into hosted-agent
registration import only what they need at the call site.
"""

from .deploy import HostedAgentDeploymentResult, deploy_hosted_agent_version
from .manifest import (
    HostedAgentEnvironmentVariable,
    HostedAgentManifest,
    HostedAgentProtocol,
    HostedAgentResource,
    HostedAgentTemplate,
    load_manifest,
    resolve_environment_variables,
)

__all__ = [
    "HostedAgentDeploymentResult",
    "HostedAgentEnvironmentVariable",
    "HostedAgentManifest",
    "HostedAgentProtocol",
    "HostedAgentResource",
    "HostedAgentTemplate",
    "deploy_hosted_agent_version",
    "load_manifest",
    "resolve_environment_variables",
]
