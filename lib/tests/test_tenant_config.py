"""Tests for tenant-aware connector configuration loader."""

from __future__ import annotations

import json

import pytest
from holiday_peak_lib.connectors.tenant_config import TenantConfigStore, normalize_tenant_id


class _FakeSecretResolver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def resolve_secret(self, reference: str, *, vault_url: str | None = None) -> str:
        self.calls.append((reference, vault_url))
        return f"secret::{reference}::{vault_url or 'none'}"


@pytest.mark.asyncio
async def test_load_tenant_config_and_runtime_resolution(tmp_path):
    config = {
        "connectors": {
            "inventory_scm": {
                "vendor": "sap_s4hana",
                "settings": {
                    "endpoint": "https://sap.example/api",
                    "timeout": 15,
                },
            }
        }
    }
    path = tmp_path / "tenant-acme.yaml"
    path.write_text(json.dumps(config), encoding="utf-8")

    store = TenantConfigStore(config_dir=tmp_path, env={})

    runtime = await store.resolve_connector_runtime_config("acme", "inventory_scm")

    assert runtime.tenant_id == "acme"
    assert runtime.domain == "inventory_scm"
    assert runtime.vendor == "sap_s4hana"
    assert runtime.init_kwargs["endpoint"] == "https://sap.example/api"
    assert runtime.init_kwargs["timeout"] == 15
    assert runtime.cache_key == "tenant:acme:inventory_scm:sap_s4hana"


@pytest.mark.asyncio
async def test_env_overrides_take_effect(tmp_path):
    config = {
        "connectors": {
            "inventory_scm": {
                "vendor": "sap_s4hana",
                "settings": {"timeout": 20, "retries": 2},
            }
        }
    }
    (tmp_path / "tenant-acme.yaml").write_text(json.dumps(config), encoding="utf-8")

    store = TenantConfigStore(
        config_dir=tmp_path,
        env={
            "TENANT_ACME_CONNECTOR_INVENTORY_SCM_TIMEOUT": "45",
            "CONNECTOR_INVENTORY_SCM_RETRIES": "4",
        },
    )

    runtime = await store.resolve_connector_runtime_config("acme", "inventory_scm")

    assert runtime.init_kwargs["timeout"] == 45
    assert runtime.init_kwargs["retries"] == 4


@pytest.mark.asyncio
async def test_key_vault_references_are_resolved(tmp_path):
    fake_resolver = _FakeSecretResolver()
    config = {
        "connectors": {
            "inventory_scm": {
                "vendor": "sap_s4hana",
                "key_vault_url": "https://contoso.vault.azure.net",
                "settings": {
                    "password": (
                        "@Microsoft.KeyVault("
                        "SecretUri=https://contoso.vault.azure.net/secrets/sap-password)"
                    )
                },
                "secret_refs": {
                    "client_secret": "sap-client-secret",
                },
            }
        }
    }
    (tmp_path / "tenant-acme.yaml").write_text(json.dumps(config), encoding="utf-8")

    store = TenantConfigStore(
        config_dir=tmp_path,
        env={},
        secret_resolver=fake_resolver,
    )

    runtime = await store.resolve_connector_runtime_config("acme", "inventory_scm")

    assert runtime.init_kwargs["password"].startswith(
        "secret::https://contoso.vault.azure.net/secrets/sap-password::"
    )
    assert runtime.init_kwargs["client_secret"] == (
        "secret::sap-client-secret::https://contoso.vault.azure.net"
    )
    assert fake_resolver.calls == [
        ("https://contoso.vault.azure.net/secrets/sap-password", "https://contoso.vault.azure.net"),
        ("sap-client-secret", "https://contoso.vault.azure.net"),
    ]


@pytest.mark.asyncio
async def test_missing_tenant_file_raises(tmp_path):
    store = TenantConfigStore(config_dir=tmp_path, env={})

    with pytest.raises(FileNotFoundError):
        await store.load_tenant_config("unknown")


def test_normalize_tenant_id_rejects_invalid_patterns():
    with pytest.raises(ValueError):
        normalize_tenant_id("../escape")

    with pytest.raises(ValueError):
        normalize_tenant_id("A")

    assert normalize_tenant_id("Acme_US") == "acme_us"
