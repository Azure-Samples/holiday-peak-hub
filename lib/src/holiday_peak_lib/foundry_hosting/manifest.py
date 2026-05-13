"""Pydantic model for the ``agent.yaml`` hosted-agent manifest.

The schema mirrors the canonical ``agent.manifest.yaml`` shape used by the
``azd ai agent`` tooling (see ``microsoft-foundry/foundry-samples`` →
``samples/python/hosted-agents/agent-framework/responses/01-basic``) plus a
small ``container`` block carrying the SDK-required ``cpu`` / ``memory`` /
optional ``image`` defaults that ``azd`` would otherwise inject.

Why a Pydantic model instead of raw YAML at the deploy site:

* The deploy CLI never sees a wrong-shape file silently \u2014 validation
  errors point at the offending field with a stable message.
* ``{{ENV_VAR}}`` interpolation runs in one place (``resolve_environment_variables``)
  so every service follows the same substitution contract.
* Downstream callers (CI scripts, ops runbooks) consume a typed object
  rather than passing dicts around.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

_PLACEHOLDER_PATTERN = re.compile(r"^\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}$")
"""Matches the canonical ``{{ENV_VAR}}`` placeholder used in agent.yaml."""


class HostedAgentProtocol(BaseModel):
    """One protocol entry under ``template.protocols``.

    Only ``responses`` and ``invocations`` are recognised by the Foundry
    Agent Service today; we keep ``protocol`` as a free string so previews
    of new protocols (e.g. ``activity``, ``a2a``) flow through without a
    library bump.
    """

    model_config = ConfigDict(extra="forbid")

    protocol: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)


class HostedAgentEnvironmentVariable(BaseModel):
    """One ``template.environment_variables`` entry.

    Values may be literals or ``{{NAME}}`` placeholders. Resolution happens
    in :func:`resolve_environment_variables` so the manifest stays free of
    deploy-time secrets.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    value: str = Field(...)


class HostedAgentResource(BaseModel):
    """One ``resources`` entry \u2014 model deployment bindings the agent uses."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., min_length=1)
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)


class HostedAgentTemplate(BaseModel):
    """The ``template`` block of an agent manifest."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    protocols: list[HostedAgentProtocol] = Field(default_factory=list)
    environment_variables: list[HostedAgentEnvironmentVariable] = Field(default_factory=list)

    @field_validator("kind")
    @classmethod
    def _kind_is_hosted(cls, value: str) -> str:
        """Enforce ``kind: hosted`` \u2014 the only kind this module deploys.

        ``direct-model`` / tracking-only manifests live outside this module's
        contract and the deploy script must refuse to register them.
        """
        if value != "hosted":
            raise ValueError(
                f"template.kind must be 'hosted' for hosted-agent deployment; got {value!r}"
            )
        return value


class HostedAgentContainer(BaseModel):
    """Container sizing + default image reference for hosted-agent deploys.

    ``image`` is optional in the manifest because operators almost always
    override it at deploy time with the just-pushed tag (``--image-uri``).
    When set in the YAML it acts as a default for local probes.
    """

    model_config = ConfigDict(extra="forbid")

    cpu: str = Field(default="1")
    memory: str = Field(default="2Gi")
    image: str | None = None


class HostedAgentManifest(BaseModel):
    """Top-level agent.yaml document for a Foundry hosted agent."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)
    template: HostedAgentTemplate
    container: HostedAgentContainer = Field(default_factory=HostedAgentContainer)
    resources: list[HostedAgentResource] = Field(default_factory=list)


def load_manifest(path: str | Path) -> HostedAgentManifest:
    """Read a hosted-agent manifest from ``path`` and validate the schema.

    ``path`` may point at the manifest file directly or at a directory.
    When a directory is given the loader probes for files in priority order:

    1. ``agent.manifest.yaml`` \u2014 the canonical name used by the official
       Microsoft ``foundry-samples`` repository and by ``azd ai agent init -m``.
    2. ``agent.hosted.yaml`` \u2014 the project-internal name that distinguishes
       hosted-agent manifests from the sibling ``agent.yaml`` portal-tracking
       artifact governed by ``tests/ops/test_foundry_portal_tracking_manifests.py``.
    3. ``agent.yaml`` \u2014 legacy fallback for one-file sample layouts only.
    """
    p = Path(path)
    if p.is_dir():
        candidates = (
            p / "agent.manifest.yaml",
            p / "agent.hosted.yaml",
            p / "agent.yaml",
        )
        for candidate in candidates:
            if candidate.is_file():
                p = candidate
                break
        else:
            raise FileNotFoundError(
                "no agent.manifest.yaml, agent.hosted.yaml or agent.yaml "
                f"found in directory: {path}"
            )
    if not p.exists():
        raise FileNotFoundError(f"agent manifest not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return HostedAgentManifest.model_validate(raw)


def resolve_environment_variables(
    manifest: HostedAgentManifest,
    *,
    env: dict[str, str] | None = None,
    strict: bool = True,
) -> dict[str, str]:
    """Resolve ``{{NAME}}`` placeholders in ``template.environment_variables``.

    Args:
        manifest: The validated manifest.
        env: Mapping used to look up placeholder values. Defaults to
            ``os.environ``.
        strict: When ``True`` (default) an unresolved placeholder raises
            ``KeyError`` \u2014 the deploy must fail loudly if the operator
            forgot to export a required variable. Set ``False`` to keep
            the literal placeholder string (useful for dry-runs and
            documentation rendering).

    Returns:
        ``dict[name, value]`` ready to hand to ``HostedAgentDefinition``.
    """
    source = env if env is not None else dict(os.environ)
    resolved: dict[str, str] = {}
    for entry in manifest.template.environment_variables:
        value = entry.value
        match = _PLACEHOLDER_PATTERN.match(value)
        if match:
            key = match.group(1)
            if key in source:
                value = source[key]
            elif strict:
                raise KeyError(
                    f"environment variable {key!r} required by manifest "
                    f"{manifest.name!r} is not set"
                )
        resolved[entry.name] = value
    return resolved
