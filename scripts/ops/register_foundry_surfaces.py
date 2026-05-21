#!/usr/bin/env python3
"""Plan or apply Microsoft Foundry surface registration for retail agents.

The script consumes ``apps/foundry-surfaces.yaml`` plus each agent's Hosted
manifest or Custom proxy metadata. Plan mode is deterministic and network-free.
Apply mode creates or updates Hosted Agent versions in Foundry using the Azure
AI Projects SDK; Custom Agent proxy entries are validated and emitted as
metadata-only operations because the current SDK exposes prompt, hosted, and
workflow agent definitions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "apps" / "foundry-surfaces.yaml"
DEFAULT_CPU = "0.5"
DEFAULT_MEMORY = "1Gi"
FORBIDDEN_HOSTED_ENV_PREFIXES = ("FOUNDRY_", "AGENT_")
HOSTED_APPLY_SURFACE = "hosted"
PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class SurfaceRegistrationError(RuntimeError):
    """Raised when a surface registry or manifest cannot be materialized."""


@dataclass(frozen=True)
class RegistrationInputs:
    mode: str
    environment: str
    registry_path: Path
    project_endpoint: str | None
    project_name: str | None
    acr_login_server: str | None
    image_tag: str | None
    image_map_file: Path | None
    apim_base_url: str | None
    services: tuple[str, ...]
    output: Path | None
    model_deployment_fast: str
    model_deployment_rich: str
    allow_unresolved: bool


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SurfaceRegistrationError(f"YAML file not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SurfaceRegistrationError(f"{path} must contain a YAML mapping")
    return loaded


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_image_map(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    if not path.is_file():
        raise SurfaceRegistrationError(f"Image map file not found: {path}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SurfaceRegistrationError(f"Image map must be a JSON object: {path}")
    return {str(service): str(image_ref) for service, image_ref in loaded.items()}


def _split_services(raw_services: str | None) -> tuple[str, ...]:
    if not raw_services:
        return ()
    return tuple(service.strip() for service in raw_services.split(",") if service.strip())


def _as_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SurfaceRegistrationError(f"{label} must be a mapping")
    return value


def _as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SurfaceRegistrationError(f"{label} must be a list")
    return value


def _stable_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _service_values(inputs: RegistrationInputs, service: str) -> dict[str, str]:
    values = {key: value for key, value in os.environ.items() if value != ""}
    defaults = {
        "PROJECT_ENDPOINT": inputs.project_endpoint,
        "PROJECT_NAME": inputs.project_name,
        "MODEL_DEPLOYMENT_NAME_FAST": inputs.model_deployment_fast,
        "MODEL_DEPLOYMENT_NAME_RICH": inputs.model_deployment_rich,
        "HPH_AGENT_ID_FAST": f"{service}-fast",
        "HPH_AGENT_ID_RICH": f"{service}-rich",
        "APIM_BASE_URL": inputs.apim_base_url,
    }
    for key, value in defaults.items():
        if value is not None:
            values[key] = value
    values.setdefault("REDIS_URL", "")
    return values


def _resolve_template(
    raw_value: Any,
    values: dict[str, str],
    *,
    allow_unresolved: bool,
) -> tuple[str, list[str]]:
    unresolved: list[str] = []
    raw_text = str(raw_value)

    def replace_placeholder(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in values:
            return values[name]
        unresolved.append(name)
        if allow_unresolved:
            return match.group(0)
        return ""

    resolved = PLACEHOLDER_RE.sub(replace_placeholder, raw_text)
    if unresolved and not allow_unresolved:
        joined = ", ".join(sorted(set(unresolved)))
        raise SurfaceRegistrationError(f"Unresolved required values: {joined}")
    return resolved, sorted(set(unresolved))


def _registry_services(registry: dict[str, Any], surface_name: str) -> list[str]:
    surfaces = _as_mapping(registry.get("surfaces"), "registry.surfaces")
    surface = _as_mapping(surfaces.get(surface_name), f"registry.surfaces.{surface_name}")
    agents = _as_list(surface.get("agents"), f"registry.surfaces.{surface_name}.agents")
    return [str(agent) for agent in agents]


def _requested_services(registry: dict[str, Any], inputs: RegistrationInputs) -> set[str]:
    all_services = set(_registry_services(registry, "hosted")) | set(
        _registry_services(registry, "custom")
    )
    if not inputs.services:
        return all_services

    requested = set(inputs.services)
    unknown = requested - all_services
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise SurfaceRegistrationError(f"Requested service is not in Foundry registry: {joined}")
    return requested


def _image_ref_for_service(
    service: str,
    image_map: dict[str, str],
    inputs: RegistrationInputs,
) -> str:
    mapped = image_map.get(service)
    if mapped:
        return mapped
    if inputs.acr_login_server and inputs.image_tag:
        return f"{inputs.acr_login_server.rstrip('/')}/{service}:{inputs.image_tag}"
    raise SurfaceRegistrationError(
        "Hosted surfaces require either --image-map-file or both "
        f"--acr-login-server and --image-tag (service={service})."
    )


def _materialize_hosted_env(
    service: str,
    manifest: dict[str, Any],
    inputs: RegistrationInputs,
) -> tuple[dict[str, str], list[str]]:
    template = _as_mapping(manifest.get("template"), f"{service}.template")
    env_entries = _as_list(
        template.get("environment_variables"), f"{service}.template.environment_variables"
    )
    values = _service_values(inputs, service)
    resolved_env: dict[str, str] = {}
    unresolved: list[str] = []

    for entry in env_entries:
        env_entry = _as_mapping(entry, f"{service}.template.environment_variables[]")
        name = str(env_entry.get("name") or "")
        if not name:
            raise SurfaceRegistrationError(f"Hosted env var without name for service={service}")
        if name.startswith(FORBIDDEN_HOSTED_ENV_PREFIXES):
            raise SurfaceRegistrationError(
                f"Hosted env var uses reserved Foundry prefix: {service} {name}"
            )
        value, missing = _resolve_template(
            env_entry.get("value", ""), values, allow_unresolved=inputs.allow_unresolved
        )
        resolved_env[name] = value
        unresolved.extend(missing)

    return resolved_env, sorted(set(unresolved))


def _hosted_protocols(service: str, manifest: dict[str, Any]) -> list[dict[str, str]]:
    template = _as_mapping(manifest.get("template"), f"{service}.template")
    protocols = _as_list(template.get("protocols"), f"{service}.template.protocols")
    records: list[dict[str, str]] = []
    for entry in protocols:
        protocol_entry = _as_mapping(entry, f"{service}.template.protocols[]")
        protocol = str(protocol_entry.get("protocol") or "")
        version = str(protocol_entry.get("version") or "")
        if not protocol or not version:
            raise SurfaceRegistrationError(f"Hosted protocol record is incomplete: {service}")
        records.append({"protocol": protocol, "version": version})
    return records


def _hosted_operation(
    service: str,
    inputs: RegistrationInputs,
    image_map: dict[str, str],
) -> dict[str, Any]:
    manifest_path = REPO_ROOT / "apps" / service / "agent.hosted.yaml"
    manifest = _load_yaml(manifest_path)
    template = _as_mapping(manifest.get("template"), f"{service}.template")
    metadata = _as_mapping(manifest.get("metadata"), f"{service}.metadata")
    surface = _as_mapping(metadata.get("surface"), f"{service}.metadata.surface")
    if surface.get("type") != HOSTED_APPLY_SURFACE:
        raise SurfaceRegistrationError(f"Hosted manifest has wrong surface type: {service}")
    if surface.get("replacesProductRuntime") is not False:
        raise SurfaceRegistrationError(f"Hosted manifest must not replace AKS runtime: {service}")

    env_vars, unresolved = _materialize_hosted_env(service, manifest, inputs)
    image_ref = _image_ref_for_service(service, image_map, inputs)
    agent_name = str(manifest.get("name") or service)
    agent_definition = {
        "kind": "hosted",
        "image": image_ref,
        "cpu": str(template.get("cpu") or DEFAULT_CPU),
        "memory": str(template.get("memory") or DEFAULT_MEMORY),
        "container_protocol_versions": _hosted_protocols(service, manifest),
        "environment_variables": env_vars,
    }
    definition_sha256 = _stable_sha256(agent_definition)
    operation_metadata = {
        "hphService": service,
        "hphSurfaceType": "hosted",
        "hphProductRuntime": str(surface.get("productRuntime") or "aks"),
        "hphDefinitionSha256": definition_sha256,
        "hphSourceIssue": str(manifest.get("sourceIssue") or metadata.get("sourceIssue") or "990"),
    }
    project_endpoint = (inputs.project_endpoint or "${PROJECT_ENDPOINT}").rstrip("/")
    return {
        "service": service,
        "surface": "hosted",
        "action": "create_or_update_hosted_version",
        "applySupported": True,
        "agentName": agent_name,
        "manifestPath": manifest_path.relative_to(REPO_ROOT).as_posix(),
        "agentEndpoint": (
            f"{project_endpoint}/agents/{agent_name}/endpoint/protocols/openai/v1/responses"
        ),
        "agentDefinition": agent_definition,
        "metadata": operation_metadata,
        "description": str(manifest.get("description") or "").strip(),
        "definitionSha256": definition_sha256,
        "unresolvedVariables": unresolved,
        "costImplication": "Creates Foundry Hosted Agent active-session CPU/memory billing.",
    }


def _custom_operation(service: str, inputs: RegistrationInputs) -> dict[str, Any]:
    metadata_path = REPO_ROOT / "apps" / service / ".foundry" / "agent-metadata.yaml"
    metadata = _load_yaml(metadata_path)
    surface = _as_mapping(metadata.get("surface"), f"{service}.surface")
    proxy = _as_mapping(surface.get("proxy"), f"{service}.surface.proxy")
    environments = _as_mapping(metadata.get("environments"), f"{service}.environments")
    environment_name = str(metadata.get("defaultEnvironment") or inputs.environment)
    environment = _as_mapping(
        environments.get(environment_name), f"{service}.environments.{environment_name}"
    )
    values = _service_values(inputs, service)
    endpoint, unresolved = _resolve_template(
        proxy.get("endpoint", ""), values, allow_unresolved=inputs.allow_unresolved
    )
    agent_name = str(environment.get("agentName") or service)

    if surface.get("foundryManagedCompute") is not False:
        raise SurfaceRegistrationError(f"Custom surface must not create Foundry compute: {service}")

    return {
        "service": service,
        "surface": "custom",
        "action": "validate_custom_proxy_metadata",
        "applySupported": False,
        "agentName": agent_name,
        "metadataPath": metadata_path.relative_to(REPO_ROOT).as_posix(),
        "customProxyDefinition": {
            "kind": "custom-proxy",
            "endpoint": endpoint,
            "target": str(proxy.get("target") or "existing-aks-apim-endpoint"),
            "productRuntime": str(surface.get("productRuntime") or "aks"),
            "productTrafficPath": str(surface.get("productTrafficPath") or "APIM -> AGC -> AKS"),
            "foundryManagedCompute": False,
        },
        "unresolvedVariables": unresolved,
        "skipReason": (
            "Azure AI Projects SDK 2.x supports prompt, hosted, and workflow "
            "agent definitions; this repository records Custom Agent surfaces "
            "as APIM proxy metadata with no Foundry-managed compute."
        ),
    }


def build_registration_plan(inputs: RegistrationInputs) -> dict[str, Any]:
    registry = _load_yaml(inputs.registry_path)
    image_map = _load_image_map(inputs.image_map_file)
    requested = _requested_services(registry, inputs)
    operations: list[dict[str, Any]] = []

    for service in _registry_services(registry, "hosted"):
        if service in requested:
            operations.append(_hosted_operation(service, inputs, image_map))

    for service in _registry_services(registry, "custom"):
        if service in requested:
            operations.append(_custom_operation(service, inputs))

    unresolved_operations = [
        operation
        for operation in operations
        if operation.get("unresolvedVariables")
    ]
    if unresolved_operations and inputs.mode == "apply":
        details = "; ".join(
            f"{operation['service']}={','.join(operation['unresolvedVariables'])}"
            for operation in unresolved_operations
        )
        raise SurfaceRegistrationError(f"Apply mode has unresolved variables: {details}")

    hosted_count = sum(1 for operation in operations if operation["surface"] == "hosted")
    custom_count = sum(1 for operation in operations if operation["surface"] == "custom")
    return {
        "schemaVersion": "1.0",
        "mode": inputs.mode,
        "environment": inputs.environment,
        "projectEndpoint": inputs.project_endpoint or "${PROJECT_ENDPOINT}",
        "sourceRegistry": inputs.registry_path.relative_to(REPO_ROOT).as_posix(),
        "policy": registry.get("policy", {}),
        "counts": {
            "hosted": hosted_count,
            "custom": custom_count,
            "total": len(operations),
        },
        "operations": operations,
    }


def _version_metadata(version: object) -> dict[str, str]:
    if isinstance(version, dict):
        metadata = version.get("metadata")
    else:
        metadata = getattr(version, "metadata", None)
    if not isinstance(metadata, dict):
        return {}
    return {str(key): str(value) for key, value in metadata.items()}


def _latest_definition_hash(agents_client: object, agent_name: str) -> str | None:
    list_versions = getattr(agents_client, "list_versions", None)
    if not callable(list_versions):
        return None
    versions = list(list_versions(agent_name=agent_name))
    if not versions:
        return None
    return _version_metadata(versions[0]).get("hphDefinitionSha256")


def _hosted_definition_model(agent_definition: dict[str, Any]) -> object:
    try:
        from azure.ai.projects.models import HostedAgentDefinition, ProtocolVersionRecord
    except ImportError as exc:  # pragma: no cover - import-time failure in CI env only
        raise SurfaceRegistrationError(
            "Apply mode requires azure-ai-projects with HostedAgentDefinition support."
        ) from exc

    protocol_records = [
        ProtocolVersionRecord(protocol=entry["protocol"], version=entry["version"])
        for entry in agent_definition["container_protocol_versions"]
    ]
    return HostedAgentDefinition(
        image=agent_definition["image"],
        cpu=agent_definition["cpu"],
        memory=agent_definition["memory"],
        container_protocol_versions=protocol_records,
        environment_variables=agent_definition["environment_variables"],
    )


def apply_registration_plan(plan: dict[str, Any], inputs: RegistrationInputs) -> list[dict[str, str]]:
    if not inputs.project_endpoint:
        raise SurfaceRegistrationError("Apply mode requires --project-endpoint or PROJECT_ENDPOINT.")

    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:  # pragma: no cover - import-time failure in CI env only
        raise SurfaceRegistrationError(
            "Apply mode requires azure-ai-projects and azure-identity."
        ) from exc

    credential = DefaultAzureCredential()
    client_kwargs: dict[str, object] = {
        "endpoint": inputs.project_endpoint,
        "credential": credential,
        "allow_preview": True,
    }
    if inputs.project_name:
        client_kwargs["project_name"] = inputs.project_name

    results: list[dict[str, str]] = []
    with AIProjectClient(**client_kwargs) as client:  # type: ignore[arg-type]
        agents_client = client.agents
        for operation in plan["operations"]:
            if operation["surface"] != HOSTED_APPLY_SURFACE:
                results.append(
                    {
                        "service": operation["service"],
                        "surface": operation["surface"],
                        "status": "metadata-only",
                    }
                )
                continue

            agent_name = operation["agentName"]
            desired_hash = operation["definitionSha256"]
            if _latest_definition_hash(agents_client, agent_name) == desired_hash:
                results.append(
                    {"service": operation["service"], "surface": "hosted", "status": "unchanged"}
                )
                continue

            definition = _hosted_definition_model(operation["agentDefinition"])
            agents_client.create_version(
                agent_name=agent_name,
                definition=definition,
                metadata=operation["metadata"],
                description=operation.get("description") or None,
            )
            results.append(
                {
                    "service": operation["service"],
                    "surface": "hosted",
                    "status": "created-or-updated",
                }
            )
    return results


def _inputs_from_args(args: argparse.Namespace) -> RegistrationInputs:
    mode = str(args.mode).lower()
    allow_unresolved = bool(args.allow_unresolved or mode == "plan")
    return RegistrationInputs(
        mode=mode,
        environment=args.environment,
        registry_path=Path(args.registry).resolve(),
        project_endpoint=args.project_endpoint or os.getenv("PROJECT_ENDPOINT"),
        project_name=args.project_name or os.getenv("PROJECT_NAME"),
        acr_login_server=args.acr_login_server or os.getenv("AZURE_CONTAINER_REGISTRY"),
        image_tag=args.image_tag
        or os.getenv("DEPLOY_SOURCE_SHA")
        or os.getenv("IMAGE_TAG")
        or os.getenv("GITHUB_SHA"),
        image_map_file=Path(args.image_map_file).resolve() if args.image_map_file else None,
        apim_base_url=args.apim_base_url or os.getenv("APIM_BASE_URL"),
        services=_split_services(args.services),
        output=Path(args.output).resolve() if args.output else None,
        model_deployment_fast=args.model_deployment_fast,
        model_deployment_rich=args.model_deployment_rich,
        allow_unresolved=allow_unresolved,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plan", "apply"), default="plan")
    parser.add_argument("--environment", default=os.getenv("AZURE_ENV_NAME", "dev"))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--project-endpoint", default=None)
    parser.add_argument("--project-name", default=None)
    parser.add_argument("--acr-login-server", default=None)
    parser.add_argument("--image-tag", default=None)
    parser.add_argument("--image-map-file", default=None)
    parser.add_argument("--apim-base-url", default=None)
    parser.add_argument("--services", default="")
    parser.add_argument("--output", default=None)
    parser.add_argument("--model-deployment-fast", default="gpt-5-nano")
    parser.add_argument("--model-deployment-rich", default="gpt-5")
    parser.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="Keep unresolved ${VAR} placeholders in the emitted plan.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        inputs = _inputs_from_args(args)
        plan = build_registration_plan(inputs)
        if inputs.output:
            _write_json(inputs.output, plan)
        print(
            "[foundry-surfaces] "
            f"mode={inputs.mode} hosted={plan['counts']['hosted']} "
            f"custom={plan['counts']['custom']} total={plan['counts']['total']}"
        )

        if inputs.mode == "apply":
            results = apply_registration_plan(plan, inputs)
            for result in results:
                print(
                    "[foundry-surfaces] "
                    f"service={result['service']} surface={result['surface']} "
                    f"status={result['status']}"
                )
        return 0
    except SurfaceRegistrationError as exc:
        print(f"[foundry-surfaces] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())