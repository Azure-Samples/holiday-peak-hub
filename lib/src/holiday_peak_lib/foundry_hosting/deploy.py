"""Register a Foundry V3 hosted-agent version using the official SDK.

This module is a thin, testable wrapper around::

    AIProjectClient(endpoint, credential).agents.create_version(
        agent_name=manifest.name,
        definition=HostedAgentDefinition(
            container_protocol_versions=[ProtocolVersionRecord(...)],
            cpu=..., memory=..., image=..., environment_variables=...,
        ),
    )

The wrapper takes care of:

* lazy imports of ``azure-ai-projects`` / ``azure.identity`` so unit tests
  do not need the SDKs installed,
* placeholder resolution for ``template.environment_variables``,
* optional polling until the version reports a terminal status (``active``
  or ``failed``),
* shaping the result into a small dataclass-style return that callers can
  log and assert against.

Container coordinates (``cpu``, ``memory``, ``image``) come from the call
site \u2014 typically a CI step that has just pushed a new image tag to ACR.
Falling back to the manifest's ``container`` block is intentional so local
operators can iterate from a YAML file without flag soup.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .manifest import HostedAgentManifest, resolve_environment_variables

logger = logging.getLogger(__name__)

# Per Microsoft Foundry hosted-agent docs the version lifecycle is
# ``creating -> active`` (success terminal), or ``failed`` / ``deleted``
# (failure terminals). ``deleting`` is transient and resolves to ``deleted``.
# Source: learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent.
_TERMINAL_STATUSES = {"active", "failed", "deleted"}
_FAILED_STATUSES = {"failed", "deleted"}
_SUCCESS_STATUS = "active"


@dataclass
class HostedAgentDeploymentResult:
    """Outcome of ``deploy_hosted_agent_version``.

    Attributes:
        agent_name: Name of the agent registered in Foundry.
        version: Version identifier returned by the platform (or ``None``
            if the SDK did not surface one before polling timed out).
        status: Last status string observed for the version.
        endpoint_url: Public Responses endpoint, when surfaced by the
            platform (``{project_endpoint}/agents/{name}/endpoint/...``).
        raw: The raw SDK response object for callers that need full detail.
        polled_seconds: How long the helper waited for a terminal status.
    """

    agent_name: str
    version: str | None
    status: str
    endpoint_url: str | None = None
    raw: Any | None = None
    polled_seconds: float = 0.0
    polling_attempts: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status.lower() == _SUCCESS_STATUS


def _build_definition(
    manifest: HostedAgentManifest,
    *,
    image: str,
    cpu: str,
    memory: str,
    environment_variables: dict[str, str],
) -> Any:
    """Construct ``HostedAgentDefinition`` lazily so the SDK is optional at
    import time (tests stub the wrapper instead).
    """
    from azure.ai.projects.models import (  # type: ignore[import-not-found]
        AgentProtocol,
        HostedAgentDefinition,
        ProtocolVersionRecord,
    )

    container_protocol_versions = []
    for proto in manifest.template.protocols:
        try:
            protocol_value = AgentProtocol(proto.protocol)
        except ValueError:
            # New / preview protocols not yet in the enum: pass the string
            # through so the platform's own validation can speak.
            protocol_value = proto.protocol
        container_protocol_versions.append(
            ProtocolVersionRecord(protocol=protocol_value, version=proto.version)
        )

    return HostedAgentDefinition(
        container_protocol_versions=container_protocol_versions,
        cpu=cpu,
        memory=memory,
        image=image,
        environment_variables=environment_variables,
    )


def _build_project_client(
    *,
    project_endpoint: str,
    credential: Any | None,
) -> Any:
    """Build the ``AIProjectClient`` with the V3 hosted-agent preview flag.

    The ``allow_preview=True`` keyword is **mandatory** for hosted-agent
    operations (``agents.create_version``, ``agents.get_version``). Without
    it the SDK routes calls to the legacy V2 surface and ``create_version``
    is not exposed. Per
    learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent.
    """
    from azure.ai.projects import AIProjectClient  # type: ignore[import-not-found]

    if credential is None:
        from azure.identity import DefaultAzureCredential  # type: ignore[import-not-found]

        credential = DefaultAzureCredential()
    return AIProjectClient(
        endpoint=project_endpoint,
        credential=credential,
        allow_preview=True,
    )


def _extract(obj: Any, *names: str) -> Any:
    """Read the first attribute / key that exists on ``obj``.

    The SDK shapes vary slightly across preview builds (snake_case vs
    camelCase, attrs vs ``additional_properties``). Centralising the
    lookup keeps the deploy code stable across builds.
    """
    for name in names:
        if obj is None:
            return None
        value = getattr(obj, name, None)
        if value is not None:
            return value
        if isinstance(obj, dict):
            value = obj.get(name)
            if value is not None:
                return value
    return None


def _normalize_status(raw_status: Any) -> str:
    """Return the canonical lowercase status string.

    The Foundry SDK deserialises the JSON ``"status": "failed"`` field
    into an ``AgentVersionStatus`` enum whose ``str()`` representation is
    ``"AgentVersionStatus.FAILED"``. Lowercasing that gives
    ``"agentversionstatus.failed"`` which does not match our terminal
    sets. We therefore prefer the enum's ``.value`` and only fall back
    to ``str()`` for plain strings. As a last resort we strip any
    ``Enum.MEMBER`` dotted prefix so unexpected shapes still normalise
    to ``"failed"`` / ``"active"`` rather than the dotted form.
    """
    if raw_status is None:
        return "unknown"
    value = getattr(raw_status, "value", None)
    if isinstance(value, str):
        return value.lower()
    text = str(raw_status).lower()
    if "." in text:
        # Handles ``agentversionstatus.failed`` -> ``failed``.
        text = text.rsplit(".", 1)[-1]
    return text


def deploy_hosted_agent_version(
    manifest: HostedAgentManifest,
    *,
    image_uri: str | None = None,
    project_endpoint: str,
    cpu: str | None = None,
    memory: str | None = None,
    credential: Any | None = None,
    environment_overrides: dict[str, str] | None = None,
    poll: bool = True,
    poll_interval_seconds: float = 5.0,
    poll_timeout_seconds: float = 600.0,
    project_client: Any | None = None,
) -> HostedAgentDeploymentResult:
    """Register (or update) a hosted-agent version in Azure AI Foundry.

    Args:
        manifest: Validated manifest produced by
            :func:`holiday_peak_lib.foundry_hosting.load_manifest`.
        image_uri: Container image to register. When ``None`` the helper
            falls back to ``manifest.container.image``; if both are missing
            ``ValueError`` is raised because there is nothing to deploy.
        project_endpoint: ``{account}.services.ai.azure.com/api/projects/{project}``
            \u2014 typically the value of ``PROJECT_ENDPOINT``.
        cpu / memory: Container sizing. Default to the manifest values
            (``container.cpu`` / ``container.memory``).
        credential: Azure credential object. When omitted,
            ``DefaultAzureCredential()`` is constructed lazily so unit tests
            need not install ``azure-identity``.
        environment_overrides: Optional dict added to the resolved
            ``template.environment_variables`` before sending to the
            platform. Useful for one-off operator overrides without
            mutating the manifest on disk.
        poll: Block until the version reports a terminal status. Disable
            for fire-and-forget calls (e.g. canary preview).
        poll_interval_seconds / poll_timeout_seconds: Polling controls.
        project_client: Pre-built ``AIProjectClient``. Test-only seam \u2014
            production callers should leave this ``None`` and let the
            helper build the client.

    Returns:
        :class:`HostedAgentDeploymentResult` with the final observed status.
    """
    image = image_uri or manifest.container.image
    if not image:
        raise ValueError(
            "image_uri is required: pass --image-uri at deploy time or set "
            "container.image in the manifest"
        )

    resolved_env = resolve_environment_variables(manifest)
    if environment_overrides:
        resolved_env.update(environment_overrides)

    definition = _build_definition(
        manifest,
        image=image,
        cpu=cpu or manifest.container.cpu,
        memory=memory or manifest.container.memory,
        environment_variables=resolved_env,
    )

    client = project_client or _build_project_client(
        project_endpoint=project_endpoint, credential=credential
    )

    logger.info(
        "foundry_hosted_agent_create_version agent=%s image=%s cpu=%s memory=%s",
        manifest.name,
        image,
        cpu or manifest.container.cpu,
        memory or manifest.container.memory,
    )
    create_response = client.agents.create_version(
        agent_name=manifest.name,
        definition=definition,
    )

    version_id = _extract(create_response, "version", "name", "id")
    status = _normalize_status(_extract(create_response, "status", "provisioning_state"))
    endpoint_url = _extract(create_response, "endpoint_url", "endpoint")

    result = HostedAgentDeploymentResult(
        agent_name=manifest.name,
        version=str(version_id) if version_id is not None else None,
        status=status,
        endpoint_url=str(endpoint_url) if endpoint_url else None,
        raw=create_response,
    )

    if not poll or status in _TERMINAL_STATUSES:
        if status in _FAILED_STATUSES:
            raise RuntimeError(
                f"hosted-agent registration failed: agent={manifest.name} "
                f"version={result.version} status={status}"
            )
        return result

    return _poll_until_terminal(
        client=client,
        result=result,
        interval_seconds=poll_interval_seconds,
        timeout_seconds=poll_timeout_seconds,
    )


def _poll_until_terminal(
    *,
    client: Any,
    result: HostedAgentDeploymentResult,
    interval_seconds: float,
    timeout_seconds: float,
) -> HostedAgentDeploymentResult:
    """Poll ``get_version`` until the status is terminal or the timeout fires.

    Implemented synchronously because ``AIProjectClient.agents`` is a
    synchronous client in the GA SDK. Callers needing async should wrap
    this helper in ``asyncio.to_thread``.
    """
    started = time.monotonic()
    attempts = 0
    status = result.status
    raw: Any = result.raw

    while status not in _TERMINAL_STATUSES:
        elapsed = time.monotonic() - started
        if elapsed >= timeout_seconds:
            result.polled_seconds = elapsed
            result.polling_attempts = attempts
            raise TimeoutError(
                f"hosted-agent registration did not reach a terminal status "
                f"within {timeout_seconds:.0f}s: agent={result.agent_name} "
                f"version={result.version} last_status={status}"
            )
        time.sleep(interval_seconds)
        attempts += 1
        try:
            raw = client.agents.get_version(
                agent_name=result.agent_name,
                version=result.version,
            )
        except TypeError:
            # Older preview builds accepted positional args only.
            raw = client.agents.get_version(result.agent_name, result.version)
        status = _normalize_status(_extract(raw, "status", "provisioning_state") or status)
        result.status = status
        endpoint_url = _extract(raw, "endpoint_url", "endpoint")
        if endpoint_url:
            result.endpoint_url = str(endpoint_url)
        result.raw = raw
        logger.info(
            "foundry_hosted_agent_poll agent=%s version=%s status=%s elapsed=%.1fs",
            result.agent_name,
            result.version,
            status,
            elapsed,
        )

    result.polled_seconds = time.monotonic() - started
    result.polling_attempts = attempts
    if status in _FAILED_STATUSES:
        raise RuntimeError(
            f"hosted-agent registration failed: agent={result.agent_name} "
            f"version={result.version} status={status}"
        )
    return result


async def deploy_hosted_agent_version_async(
    manifest: HostedAgentManifest,
    **kwargs: Any,
) -> HostedAgentDeploymentResult:
    """Async wrapper for callers running inside an event loop.

    The underlying ``AIProjectClient.agents.create_version`` is synchronous,
    so we shed the work to a worker thread. Exposed as a separate function
    rather than overloaded keyword so call sites stay self-documenting.
    """
    return await asyncio.to_thread(deploy_hosted_agent_version, manifest, **kwargs)
