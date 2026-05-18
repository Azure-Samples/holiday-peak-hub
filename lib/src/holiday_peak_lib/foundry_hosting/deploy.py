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
import json
import logging
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from .manifest import HostedAgentManifest, resolve_environment_variables

logger = logging.getLogger(__name__)

# Per Microsoft Foundry hosted-agent docs the version lifecycle is
# ``creating -> active`` (success terminal), or ``failed`` / ``deleted``
# (failure terminals). ``deleting`` is transient and resolves to ``deleted``.
# Source: learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent.
_TERMINAL_STATUSES = {"active", "failed", "deleted"}
_FAILED_STATUSES = {"failed", "deleted"}
_SUCCESS_STATUS = "active"

# Built-in role name granted to per-version managed identities so they can
# write into the Foundry storage surface (POST /storage/responses, etc.).
# Confirmed against the live ``aipholidaris`` project: without this role,
# every Playground / Responses call returns 401 ``Principal does not have
# access to API/Operation`` even though the container itself runs fine.
# The ``azd`` / VS-Code extension deploy paths grant it implicitly; the
# SDK path (this module) does not, so we grant it here.
_DEFAULT_FOUNDRY_ROLE_NAME = "Foundry User"

# Return shape contract for the ``role_granter`` callable seam. The dict
# is shallow on purpose (gets logged + surfaced in result.extras) so test
# fakes can return literal payloads without depending on the SDK.
RoleGrantResult = dict[str, str]
RoleGranter = Callable[..., RoleGrantResult | None]


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

    Order of precedence:

    1. ``getattr`` -- covers ``SimpleNamespace`` fakes and SDK shapes
       that expose fields as real attributes.
    2. ``isinstance(obj, dict)`` -- covers plain ``dict`` responses.
    3. ``isinstance(obj, Mapping)`` -- covers SDK model types like
       ``azure.ai.projects.models.AgentVersionDetails`` (returned by
       ``client.agents.get_version`` in ``azure-ai-projects 2.0.1``).
       Those models subclass ``collections.abc.MutableMapping`` but
       are NOT ``dict`` and do NOT expose fields via ``getattr`` --
       ``getattr(obj, 'status', None)`` returns ``None`` while
       ``obj['status']`` returns ``'failed'``. Without this branch the
       poll loop logged ``status=unknown`` for ~164s on real Azure
       deployments and timed out instead of failing fast.
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
        elif isinstance(obj, Mapping):
            try:
                value = obj[name]
            except (KeyError, TypeError):
                value = None
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


def _parse_version_number(value: str) -> int | None:
    """Parse the leading integer from a version label.

    Tolerant of ``"v3"``, ``"3"``, and ``"3.1.0"`` shapes. Returns ``None``
    when the label is not numeric, which lets the picker treat it as a
    last-resort candidate instead of crashing.
    """
    stripped = value.lstrip("vV")
    if "." in stripped:
        stripped = stripped.split(".", 1)[0]
    try:
        return int(stripped)
    except ValueError:
        return None


def _pick_latest_version(versions: Any) -> tuple[Any, str | None]:
    """Return the entry with the highest numeric version label.

    Iterates ``versions`` (typically the return value of
    ``client.agents.list_versions``) and selects the entry whose label
    parses to the largest integer. Non-numeric labels are kept as a
    last-resort candidate so an exotic preview shape never causes the
    resolver to silently drop a real version.
    """
    best_num = -1
    best_obj: Any = None
    best_str: str | None = None
    for entry in versions:
        raw = _extract(entry, "version", "name", "id")
        if raw is None:
            continue
        raw_str = str(raw)
        num = _parse_version_number(raw_str)
        if num is None:
            if best_obj is None:
                best_obj = entry
                best_str = raw_str
            continue
        if num > best_num:
            best_num = num
            best_obj = entry
            best_str = raw_str
    return best_obj, best_str


def _resolve_latest_version(
    client: Any,
    agent_name: str,
    create_response: Any,
) -> tuple[str | None, Any]:
    """Re-resolve the genuinely newest version after ``create_version``.

    Adapter + Chain of Responsibility: the Azure AI Projects preview SDK
    has been observed to return ``create_version`` responses whose
    ``.version`` / ``.status`` reflect the *previous* version, not the
    one just created (root cause of the false "v3 active" report seen
    against ``inventory-health-check``). This helper queries the
    platform after the fact and returns the actually-latest version,
    falling back to weaker signals as the SDK surface allows.

    Resolution order:

    1. ``client.agents.list_versions(agent_name=...)`` -- iterate and
       pick the entry with the highest numeric version label.
    2. ``client.agents.get_agent(agent_name=...)`` -- read
       ``latest_version`` / ``version``, then ``get_version`` for the
       full object.
    3. Fall back to ``create_response`` (older SDK builds).

    Whichever path resolves logs a structured INFO line of the form::

        foundry_hosted_agent_resolved_version agent=<name>
            reported=<from_create_response> resolved=<from_list>
            path=<list_versions|get_agent|create_response>

    so divergence between what the SDK reported and what the platform
    actually holds is visible in operator logs.

    Returns:
        ``(version_str_or_none, version_obj)``. ``version_obj`` is the
        raw SDK payload for the resolved path -- the original
        ``create_response`` for the final fallback.
    """
    reported_raw = _extract(create_response, "version", "name", "id")
    reported_str = str(reported_raw) if reported_raw is not None else None

    agents = getattr(client, "agents", None)

    # Path 1: list_versions -- strongest signal.
    list_versions = getattr(agents, "list_versions", None)
    if list_versions is not None:
        try:
            try:
                versions = list_versions(agent_name=agent_name)
            except TypeError:
                # Older preview builds accepted positional args only.
                versions = list_versions(agent_name)
            latest_obj, latest_str = _pick_latest_version(versions)
            if latest_obj is not None:
                # The ``list_versions`` endpoint is DENORMALIZED on the
                # preview surface: every entry reports ``status: "active"``
                # regardless of the true per-version state. Refresh via
                # ``get_version`` so the caller sees the real status, not
                # the stale list-entry value. This mirrors Path 2 below and
                # prevents the deploy from short-circuiting the poll loop
                # on a fake "active" terminal status (the root cause of the
                # false-positive ``v3 active`` reports observed against
                # ``inventory-health-check`` when the underlying image
                # actually failed to be pulled by Foundry).
                get_version_fn = getattr(agents, "get_version", None)
                resolved_obj: Any = latest_obj
                if get_version_fn is not None and latest_str is not None:
                    try:
                        try:
                            resolved_obj = get_version_fn(agent_name=agent_name, version=latest_str)
                        except TypeError:
                            resolved_obj = get_version_fn(agent_name, latest_str)
                    except Exception:  # pylint: disable=broad-exception-caught
                        logger.warning(
                            "foundry_hosted_agent_resolve_get_version_after_list_error "
                            "agent=%s version=%s",
                            agent_name,
                            latest_str,
                            exc_info=True,
                        )
                        resolved_obj = latest_obj
                logger.info(
                    "foundry_hosted_agent_resolved_version agent=%s "
                    "reported=%s resolved=%s path=list_versions",
                    agent_name,
                    reported_str,
                    latest_str,
                )
                return latest_str, resolved_obj
        except Exception:  # pylint: disable=broad-exception-caught
            # Preview SDK surface is volatile: fall through rather than
            # break deploy when list_versions exists but errors.
            logger.warning(
                "foundry_hosted_agent_resolve_list_versions_error agent=%s",
                agent_name,
                exc_info=True,
            )

    # Path 2: get_agent + get_version.
    get_agent = getattr(agents, "get_agent", None)
    if get_agent is not None:
        try:
            try:
                agent_obj = get_agent(agent_name=agent_name)
            except TypeError:
                agent_obj = get_agent(agent_name)
            latest = _extract(agent_obj, "latest_version", "version")
            if latest is not None:
                latest_str = str(latest)
                try:
                    version_obj = agents.get_version(agent_name=agent_name, version=latest_str)
                except TypeError:
                    version_obj = agents.get_version(agent_name, latest_str)
                logger.info(
                    "foundry_hosted_agent_resolved_version agent=%s "
                    "reported=%s resolved=%s path=get_agent",
                    agent_name,
                    reported_str,
                    latest_str,
                )
                return latest_str, version_obj
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning(
                "foundry_hosted_agent_resolve_get_agent_error agent=%s",
                agent_name,
                exc_info=True,
            )

    # Path 3: trust create_response as today.
    logger.info(
        "foundry_hosted_agent_resolved_version agent=%s reported=%s "
        "resolved=%s path=create_response",
        agent_name,
        reported_str,
        reported_str,
    )
    return reported_str, create_response


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
    auto_grant_role: bool = True,
    foundry_role_name: str = _DEFAULT_FOUNDRY_ROLE_NAME,
    project_scope: str | None = None,
    role_granter: RoleGranter | None = None,
    scope_resolver: Callable[[str], str | None] | None = None,
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
            helper build the client.        auto_grant_role: When ``True`` (default), the helper grants
            ``foundry_role_name`` to the per-version managed identity on
            the project scope once the version reaches ``active``. This
            resolves the recurring 401 ``Principal does not have access
            to API/Operation`` on ``POST /storage/responses`` that
            otherwise breaks every Playground / Responses invocation.
            Set to ``False`` for environments where role assignment is
            managed out of band.
        foundry_role_name: Built-in role to grant. Defaults to
            ``"Foundry User"``, the role validated against the live
            ``aipholidaris`` project.
        project_scope: Optional ARM scope override for the role grant
            (``/subscriptions/.../accounts/{a}/projects/{p}``). When
            ``None``, the helper derives it from ``project_endpoint``
            via ``az resource list``.
        role_granter: Test seam for the role-assignment subprocess. The
            default :func:`_grant_role_via_az` shells out to ``az role
            assignment create`` and is idempotent on
            ``RoleAssignmentExists``.
        scope_resolver: Test seam for the scope-derivation subprocess.
            The default :func:`_resolve_ai_account_resource_id_via_az`
            shells out to ``az resource list``.
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

    # The preview SDK has been observed to return a ``create_version``
    # response whose ``.version`` / ``.status`` reflect the *previous*
    # version rather than the one just created. Re-resolve from the
    # platform so ``result`` reflects reality, not stale SDK state.
    version_id, version_obj = _resolve_latest_version(client, manifest.name, create_response)
    status = _normalize_status(_extract(version_obj, "status", "provisioning_state"))
    endpoint_url = _extract(version_obj, "endpoint_url", "endpoint")

    result = HostedAgentDeploymentResult(
        agent_name=manifest.name,
        version=str(version_id) if version_id is not None else None,
        status=status,
        endpoint_url=str(endpoint_url) if endpoint_url else None,
        raw=version_obj,
    )

    if not poll or status in _TERMINAL_STATUSES:
        if status in _FAILED_STATUSES:
            raise RuntimeError(
                f"hosted-agent registration failed: agent={manifest.name} "
                f"version={result.version} status={status}"
            )
        _maybe_grant_foundry_user(
            result=result,
            project_endpoint=project_endpoint,
            project_scope=project_scope,
            role_name=foundry_role_name,
            auto_grant_role=auto_grant_role,
            role_granter=role_granter,
            scope_resolver=scope_resolver,
        )
        return result

    polled = _poll_until_terminal(
        client=client,
        result=result,
        interval_seconds=poll_interval_seconds,
        timeout_seconds=poll_timeout_seconds,
    )
    _maybe_grant_foundry_user(
        result=polled,
        project_endpoint=project_endpoint,
        project_scope=project_scope,
        role_name=foundry_role_name,
        auto_grant_role=auto_grant_role,
        role_granter=role_granter,
        scope_resolver=scope_resolver,
    )
    return polled


def _maybe_grant_foundry_user(
    *,
    result: HostedAgentDeploymentResult,
    project_endpoint: str,
    project_scope: str | None,
    role_name: str,
    auto_grant_role: bool,
    role_granter: RoleGranter | None,
    scope_resolver: Callable[[str], str | None] | None,
) -> None:
    """Wrap :func:`_ensure_foundry_user_grant` so errors surface in ``extras``
    without breaking a successful deploy.

    A failed role grant is recoverable (the operator can re-run the script
    or apply ``az role assignment create`` by hand) and should not invalidate
    the version that the platform just activated. We therefore record the
    failure under ``result.extras['role_grant']`` and continue. The next
    deploy will re-attempt and either succeed or surface the same error.
    """
    if not auto_grant_role:
        result.extras.setdefault(
            "role_grant", {"status": "skipped", "reason": "auto_grant_role=False"}
        )
        return
    if result.status != _SUCCESS_STATUS:
        # Defensive: poll only returns ``active``; this branch covers any
        # future change to the early-return path that lands a non-active
        # status here.
        result.extras.setdefault(
            "role_grant", {"status": "skipped", "reason": f"status={result.status}"}
        )
        return
    granter = role_granter or _grant_role_via_az
    try:
        _ensure_foundry_user_grant(
            result=result,
            project_endpoint=project_endpoint,
            project_scope=project_scope,
            role_name=role_name,
            role_granter=granter,
            scope_resolver=scope_resolver,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "foundry_hosted_agent_role_grant_failed agent=%s version=%s error=%s",
            result.agent_name,
            result.version,
            exc,
            exc_info=True,
        )
        result.extras["role_grant"] = {
            "status": "failed",
            "error": str(exc),
            "role_name": role_name,
        }


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


# ---------------------------------------------------------------------------
# Foundry User role auto-grant (resolves operational finding O3 / issue #1107)
# ---------------------------------------------------------------------------
#
# When deploying via this module's SDK path, ``create_version`` mints a per-
# version managed identity for the agent container, but does **not** grant it
# the ``Foundry User`` role on the project scope. The ``azd`` / VS-Code
# extension deploy paths grant it implicitly via their own orchestration.
#
# Without this role, the running container can read storage but cannot write,
# so the Foundry runtime fails persistence at terminal events:
#
#     Foundry storage POST .../storage/responses?api-version=v1 -> 401
#     Principal does not have access to API/Operation.
#
# Surfacing this auto-grant inside ``deploy_hosted_agent_version`` keeps the
# operational invariant in one place and avoids relying on a separate runbook
# step that operators can forget. The grant is idempotent: an existing
# assignment is treated as success (logged but not raised).


def _extract_principal_id(version_obj: Any) -> str | None:
    """Read the per-version managed-identity principal id from a version object.

    Probes the field shapes observed in ``azure-ai-projects`` preview builds
    in order:

    1. ``version_obj.instance_identity.principal_id`` (current GA-aligned shape)
    2. ``version_obj.managed_identity.principal_id`` (older preview alias)
    3. ``version_obj.identity.principal_id``         (legacy ARM-style alias)

    Returns ``None`` when the SDK has not surfaced the principal yet -- which
    can happen if the version status was not polled to terminal. Callers must
    therefore only invoke this helper after a successful poll.
    """
    for container_key in ("instance_identity", "managed_identity", "identity"):
        container = _extract(version_obj, container_key)
        if container is None:
            continue
        principal = _extract(container, "principal_id", "principalId")
        if principal:
            return str(principal)
    return None


def _derive_project_scope_from_endpoint(
    project_endpoint: str,
    *,
    scope_resolver: Callable[[str], str | None] | None = None,
    subscription_id: str | None = None,
) -> str:
    """Build the ARM scope string for a Foundry project endpoint.

    Foundry project endpoints have the shape::

        https://{account}.services.ai.azure.com/api/projects/{project}

    The ARM scope used for role assignment is::

        /subscriptions/{sub}/resourceGroups/{rg}/providers/
        Microsoft.CognitiveServices/accounts/{account}/projects/{project}

    We do not have ``{sub}`` / ``{rg}`` from the endpoint alone. The default
    ``scope_resolver`` shells out to ``az resource list`` to look up the
    Cognitive Services account by name. Operators in restricted-permission
    environments can pre-compute the scope and pass it explicitly via
    :func:`deploy_hosted_agent_version`'s ``project_scope`` parameter instead.
    """
    parsed = urlparse(project_endpoint)
    host = parsed.hostname or ""
    if not host:
        raise ValueError(
            f"Cannot derive scope from endpoint with missing host: {project_endpoint!r}"
        )
    account = host.split(".", 1)[0]
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 3 or path_parts[0] != "api" or path_parts[1] != "projects":
        raise ValueError(f"Unexpected Foundry project endpoint shape: {project_endpoint!r}")
    project = path_parts[2]

    resolver = scope_resolver or _resolve_ai_account_resource_id_via_az
    account_resource_id = resolver(account)
    if not account_resource_id:
        raise RuntimeError(
            "Could not resolve the ARM resource id for Cognitive Services "
            f"account {account!r}. Pass --project-scope explicitly, or ensure "
            "`az login` has access to the subscription that owns the account."
        )
    # Preserve the subscription hint so the caller can use --subscription on
    # the role-grant az call (some tenants require it for cross-sub assignments).
    _ = subscription_id
    return f"{account_resource_id}/projects/{project}"


def _resolve_ai_account_resource_id_via_az(account_name: str) -> str | None:
    """Default scope resolver: ``az resource list``.

    Requires the operator's ``az login`` session to have ``Reader`` on the
    subscription that owns the Cognitive Services account. Returns the first
    matching resource id, or ``None`` if no account is visible.
    """
    proc = subprocess.run(  # noqa: S603,S607 -- arg list is fixed, not user input
        [
            "az",
            "resource",
            "list",
            "--resource-type",
            "Microsoft.CognitiveServices/accounts",
            "--name",
            account_name,
            "--query",
            "[0].id",
            "-o",
            "tsv",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        logger.warning(
            "foundry_hosted_agent_scope_resolve_failed account=%s rc=%d stderr=%s",
            account_name,
            proc.returncode,
            (proc.stderr or "").strip(),
        )
        return None
    resource_id = (proc.stdout or "").strip()
    return resource_id or None


def _grant_role_via_az(
    *,
    principal_id: str,
    scope: str,
    role_name: str = _DEFAULT_FOUNDRY_ROLE_NAME,
) -> RoleGrantResult | None:
    """Default ``RoleGranter`` -- shells out to ``az role assignment create``.

    Idempotent: if the assignment already exists (detected by parsing the
    Azure CLI error message), the helper logs and returns ``None`` instead
    of raising. Any other failure raises ``RuntimeError`` with the stderr
    payload so the caller can surface it.

    The subprocess invocation matches the manual runbook line for line
    (``az role assignment create --assignee-object-id ... --assignee-
    principal-type ServicePrincipal --role 'Foundry User' --scope ...``)
    so the behaviour is unchanged from what operators have been running
    by hand.
    """
    proc = subprocess.run(  # noqa: S603,S607 -- arg list is fixed, not user input
        [
            "az",
            "role",
            "assignment",
            "create",
            "--assignee-object-id",
            principal_id,
            "--assignee-principal-type",
            "ServicePrincipal",
            "--role",
            role_name,
            "--scope",
            scope,
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        try:
            payload = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            payload = {}
        assignment_id = str(payload.get("id", ""))
        logger.info(
            "foundry_hosted_agent_role_granted principal=%s role=%s scope=%s assignment_id=%s",
            principal_id,
            role_name,
            scope,
            assignment_id,
        )
        return {
            "id": assignment_id,
            "scope": scope,
            "role_name": role_name,
            "principal_id": principal_id,
        }
    stderr_lower = (proc.stderr or "").lower()
    stdout_lower = (proc.stdout or "").lower()
    if (
        "already exists" in stderr_lower
        or "already exists" in stdout_lower
        or "roleassignmentexists" in stderr_lower
    ):
        logger.info(
            "foundry_hosted_agent_role_already_granted principal=%s role=%s scope=%s",
            principal_id,
            role_name,
            scope,
        )
        return None
    raise RuntimeError(
        "`az role assignment create` failed for principal "
        f"{principal_id!r} role={role_name!r} scope={scope!r}: "
        f"rc={proc.returncode} stderr={(proc.stderr or proc.stdout or '').strip()}"
    )


def _ensure_foundry_user_grant(
    *,
    result: HostedAgentDeploymentResult,
    project_endpoint: str,
    project_scope: str | None,
    role_name: str,
    role_granter: RoleGranter,
    scope_resolver: Callable[[str], str | None] | None,
) -> None:
    """Grant ``role_name`` to the per-version MI on the project scope.

    Mutates ``result.extras['role_grant']`` with the outcome. Never raises
    on the absence of a principal id (e.g. SDK build that doesn't surface
    it yet) -- logs and records ``skipped=no_principal_id`` so the caller
    can decide whether to escalate. Raises on actual az / scope failures.
    """
    principal_id = _extract_principal_id(result.raw)
    if not principal_id:
        logger.warning(
            "foundry_hosted_agent_role_grant_skipped agent=%s version=%s reason=no_principal_id",
            result.agent_name,
            result.version,
        )
        result.extras["role_grant"] = {
            "status": "skipped",
            "reason": "no_principal_id",
            "role_name": role_name,
        }
        return

    scope = project_scope or _derive_project_scope_from_endpoint(
        project_endpoint, scope_resolver=scope_resolver
    )
    granted = role_granter(principal_id=principal_id, scope=scope, role_name=role_name)
    if granted is None:
        result.extras["role_grant"] = {
            "status": "already_exists",
            "principal_id": principal_id,
            "scope": scope,
            "role_name": role_name,
        }
        return
    result.extras["role_grant"] = {
        "status": "granted",
        "principal_id": principal_id,
        "scope": scope,
        "role_name": role_name,
        "assignment_id": granted.get("id", ""),
    }
