"""Tenant-aware connector configuration loading and secret resolution."""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, Field

_KEY_VAULT_REFERENCE_PATTERN = re.compile(
    r"^@Microsoft\.KeyVault\(SecretUri=(?P<secret_uri>[^)]+)\)$"
)
_TENANT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class SecretResolver(Protocol):
    """Protocol for resolving secret references in tenant connector config."""

    async def resolve_secret(self, reference: str, *, vault_url: str | None = None) -> str:
        """Resolve a secret reference to its value."""


class TenantConnectorConfig(BaseModel):
    """Connector configuration scoped to a single tenant/domain pair."""

    vendor: str
    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)
    secret_refs: dict[str, str] = Field(default_factory=dict)
    key_vault_url: str | None = None
    connection_pool: str | None = None


class TenantConfig(BaseModel):
    """Per-tenant connector configuration model."""

    tenant_id: str
    connectors: dict[str, TenantConnectorConfig] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorRuntimeConfig(BaseModel):
    """Resolved runtime connector settings for tenant/domain resolution."""

    tenant_id: str
    domain: str
    vendor: str
    init_kwargs: dict[str, Any] = Field(default_factory=dict)
    cache_key: str


def normalize_tenant_id(tenant_id: str) -> str:
    """Validate and normalize tenant identifiers used in config paths and cache keys."""
    normalized = tenant_id.strip().lower()
    if not _TENANT_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Invalid tenant_id format. Use 2-64 chars from [a-z0-9_-], starting with a-z/0-9."
        )
    return normalized


class KeyVaultSecretResolver:
    """Resolve Azure Key Vault secret references for tenant config."""

    def __init__(self) -> None:
        self._clients: dict[str, Any] = {}

    async def resolve_secret(self, reference: str, *, vault_url: str | None = None) -> str:
        parsed = _parse_secret_reference(reference, vault_url=vault_url)
        return await asyncio.to_thread(
            self._read_secret, parsed["vault_url"], parsed["secret_name"]
        )

    def _read_secret(self, vault_url: str, secret_name: str) -> str:
        try:
            from azure.identity import (
                DefaultAzureCredential,  # pylint: disable=import-outside-toplevel
            )
            from azure.keyvault.secrets import (
                SecretClient,  # pylint: disable=import-outside-toplevel
            )
        except ImportError as exc:  # pragma: no cover - depends on optional env
            raise RuntimeError(
                "Azure Key Vault support requires 'azure-identity' and "
                "'azure-keyvault-secrets' packages."
            ) from exc

        client = self._clients.get(vault_url)
        if client is None:
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)
            self._clients[vault_url] = client

        response = client.get_secret(secret_name)
        if response.value is None:
            raise ValueError(f"Key Vault secret '{secret_name}' returned an empty value")
        return response.value


class TenantConfigStore:
    """Load tenant config files and resolve runtime connector settings."""

    def __init__(
        self,
        *,
        config_dir: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        secret_resolver: SecretResolver | None = None,
    ) -> None:
        self._config_dir = Path(config_dir or "connectors/config")
        self._env = dict(env) if env is not None else os.environ
        self._secret_resolver = secret_resolver or KeyVaultSecretResolver()
        self._cache: dict[str, TenantConfig] = {}
        self._lock = asyncio.Lock()

    async def load_tenant_config(self, tenant_id: str, *, refresh: bool = False) -> TenantConfig:
        """Load tenant configuration from ``tenant-{tenant_id}.yaml``."""
        normalized_tenant = normalize_tenant_id(tenant_id)
        async with self._lock:
            if not refresh and normalized_tenant in self._cache:
                return self._cache[normalized_tenant]

        config_path = self._resolve_config_path(normalized_tenant)
        payload = self._read_yaml_payload(config_path)
        payload["tenant_id"] = normalized_tenant
        config = TenantConfig.model_validate(payload)

        async with self._lock:
            self._cache[normalized_tenant] = config
        return config

    async def resolve_connector_runtime_config(
        self,
        tenant_id: str,
        domain: str,
    ) -> ConnectorRuntimeConfig:
        """Resolve connector runtime configuration for tenant/domain."""
        normalized_domain = domain.strip().lower()
        config = await self.load_tenant_config(tenant_id)

        connector = config.connectors.get(normalized_domain)
        if connector is None:
            raise KeyError(f"No connector config for tenant '{tenant_id}' and domain '{domain}'")
        if not connector.enabled:
            raise ValueError(
                f"Connector '{normalized_domain}' is disabled for tenant '{tenant_id}'"
            )

        settings = await self._resolve_settings(
            tenant_id=tenant_id,
            domain=normalized_domain,
            connector=connector,
        )

        cache_key = connector.connection_pool or (
            f"tenant:{tenant_id.lower()}:{normalized_domain}:{connector.vendor.lower()}"
        )
        return ConnectorRuntimeConfig(
            tenant_id=tenant_id,
            domain=normalized_domain,
            vendor=connector.vendor,
            init_kwargs=settings,
            cache_key=cache_key,
        )

    def _resolve_config_path(self, tenant_id: str) -> Path:
        for extension in ("yaml", "yml"):
            candidate = self._config_dir / f"tenant-{tenant_id}.{extension}"
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            f"Tenant config file not found for '{tenant_id}' in '{self._config_dir}'"
        )

    @staticmethod
    def _read_yaml_payload(path: Path) -> dict[str, Any]:
        raw = path.read_text(encoding="utf-8")
        try:
            import yaml  # type: ignore  # pylint: disable=import-outside-toplevel

            payload = yaml.safe_load(raw)
            if payload is None:
                return {}
            if not isinstance(payload, dict):
                raise ValueError("Tenant config root must be a mapping")
            return payload
        except ImportError as exc:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as parse_exc:
                raise RuntimeError(
                    "Tenant config parsing requires PyYAML, or JSON-compatible content in "
                    "tenant-<id>.yaml files when PyYAML is unavailable."
                ) from parse_exc
            if not isinstance(parsed, dict):
                raise ValueError("Tenant config root must be a mapping") from exc
            return parsed

    async def _resolve_settings(
        self,
        *,
        tenant_id: str,
        domain: str,
        connector: TenantConnectorConfig,
    ) -> dict[str, Any]:
        settings: dict[str, Any] = dict(connector.settings)
        settings.update(self._environment_overrides(tenant_id=tenant_id, domain=domain))

        for key, value in list(settings.items()):
            if isinstance(value, str):
                keyvault_reference = _parse_key_vault_reference(value)
                if keyvault_reference is not None:
                    settings[key] = await self._secret_resolver.resolve_secret(
                        keyvault_reference["reference"],
                        vault_url=keyvault_reference["vault_url"],
                    )

        for key, reference in connector.secret_refs.items():
            settings[key] = await self._secret_resolver.resolve_secret(
                reference,
                vault_url=connector.key_vault_url,
            )

        return settings

    def _environment_overrides(self, *, tenant_id: str, domain: str) -> dict[str, Any]:
        overrides: dict[str, Any] = {}

        tenant_prefix = f"TENANT_{tenant_id.upper()}_CONNECTOR_{domain.upper()}_"
        global_prefix = f"CONNECTOR_{domain.upper()}_"

        for key, value in self._env.items():
            target_name: str | None = None
            if key.startswith(tenant_prefix):
                target_name = key[len(tenant_prefix) :]
            elif key.startswith(global_prefix):
                target_name = key[len(global_prefix) :]

            if target_name:
                overrides[target_name.lower()] = _coerce_scalar(value)

        return overrides


def _parse_key_vault_reference(value: str) -> dict[str, str] | None:
    match = _KEY_VAULT_REFERENCE_PATTERN.match(value.strip())
    if not match:
        return None

    secret_uri = match.group("secret_uri").strip()
    parsed = _parse_secret_reference(secret_uri, vault_url=None)
    return {
        "reference": secret_uri,
        "vault_url": parsed["vault_url"],
    }


def _parse_secret_reference(reference: str, *, vault_url: str | None) -> dict[str, str]:
    normalized = reference.strip()

    if normalized.startswith("https://") and "/secrets/" in normalized:
        parsed = urlparse(normalized)
        vault = f"{parsed.scheme}://{parsed.netloc}"
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 2 or path_parts[0].lower() != "secrets":
            raise ValueError(f"Unsupported Key Vault secret URI: {reference}")
        return {
            "vault_url": vault,
            "secret_name": path_parts[1],
        }

    if not vault_url:
        raise ValueError(
            "Secret reference must be a full Key Vault SecretUri or include key_vault_url"
        )

    return {
        "vault_url": vault_url,
        "secret_name": normalized,
    }


def _coerce_scalar(value: str) -> Any:
    normalized = value.strip()
    lower = normalized.lower()
    if lower in {"true", "false"}:
        return lower == "true"

    try:
        return int(normalized)
    except ValueError:
        pass

    try:
        return float(normalized)
    except ValueError:
        return normalized
