"""Connector registry for discovering and managing enterprise connectors."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import os
import pkgutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Type

from holiday_peak_lib.adapters.base import BaseAdapter


@dataclass(slots=True)
class ConnectorDefinition:
    """Static connector metadata for a registered connector class."""

    domain: str
    vendor: str
    connector_class: Type[Any]
    module: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConnectorRegistration:
    """Runtime registration metadata for an instantiated connector."""

    name: str
    connector: Any
    domain: str
    vendor: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConnectorHealth:
    """Health snapshot for a runtime connector."""

    ok: bool
    checked_at: str
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class ConnectorRegistry:
    """Central registry for connector discovery, lifecycle, and health tracking."""

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._definitions: dict[str, dict[str, ConnectorDefinition]] = {}
        self._registrations: dict[str, ConnectorRegistration] = {}
        self._health_cache: dict[str, ConnectorHealth] = {}
        self._lock = asyncio.Lock()
        self._monitor_task: asyncio.Task[None] | None = None
        self._env = dict(env) if env is not None else os.environ

    def register(
        self,
        domain: str,
        vendor: str,
        connector_class: Type[Any],
        *,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> None:
        """Register a connector class under a domain/vendor key."""
        normalized_domain = domain.strip().lower()
        normalized_vendor = vendor.strip().lower()
        domain_bucket = self._definitions.setdefault(normalized_domain, {})
        if not overwrite and normalized_vendor in domain_bucket:
            raise ValueError(
                f"Connector class already registered: {normalized_domain}:{normalized_vendor}"
            )
        domain_bucket[normalized_vendor] = ConnectorDefinition(
            domain=normalized_domain,
            vendor=normalized_vendor,
            connector_class=connector_class,
            module=getattr(connector_class, "__module__", ""),
            metadata=metadata or {},
        )

    def get(self, domain: str, vendor: str) -> Optional[Type[Any]]:
        """Return connector class by domain/vendor or ``None`` when unavailable."""
        definition = self.get_definition(domain, vendor)
        return definition.connector_class if definition else None

    def get_definition(self, domain: str, vendor: str) -> ConnectorDefinition | None:
        """Return full connector definition metadata by domain/vendor."""
        return self._definitions.get(domain.strip().lower(), {}).get(vendor.strip().lower())

    def list_vendors(self, domain: str) -> list[str]:
        """List available vendors for a domain."""
        return sorted(self._definitions.get(domain.strip().lower(), {}).keys())

    def list_definitions(self) -> list[ConnectorDefinition]:
        """List all registered connector class definitions."""
        return [
            definition for vendors in self._definitions.values() for definition in vendors.values()
        ]

    def configured_vendor(self, domain: str) -> str | None:
        """Return provider selected by environment for a domain, if configured."""
        env_key = f"CONNECTOR_{domain.strip().upper()}_PROVIDER"
        raw = self._env.get(env_key, "").strip().lower()
        return raw or None

    def load_settings(self, domain: str, vendor: str | None = None) -> dict[str, str]:
        """Load connector configuration from environment variables."""
        normalized_domain = domain.strip().upper()
        normalized_vendor = (vendor or "").strip().upper()
        domain_prefix = f"CONNECTOR_{normalized_domain}_"
        vendor_prefix = (
            f"CONNECTOR_{normalized_domain}_{normalized_vendor}_" if normalized_vendor else None
        )

        settings: dict[str, str] = {}
        for key, value in self._env.items():
            if key.startswith(domain_prefix):
                settings[key] = value
            if vendor_prefix and key.startswith(vendor_prefix):
                settings[key] = value
        return settings

    async def discover(self, package_root: str = "holiday_peak_lib.connectors") -> int:
        """Auto-discover connector classes from the connectors package tree."""
        root_module = importlib.import_module(package_root)
        discovered = 0

        module_names: set[str] = set()
        for module_info in pkgutil.walk_packages(
            root_module.__path__,
            prefix=f"{package_root}.",
        ):
            if not module_info.ispkg and module_info.name.endswith(".connector"):
                module_names.add(module_info.name)

        for package_path in root_module.__path__:
            root_path = Path(package_path)
            for connector_file in root_path.rglob("connector.py"):
                relative_parts = connector_file.relative_to(root_path).with_suffix("").parts
                module_names.add(".".join((package_root, *relative_parts)))

        for module_name in sorted(module_names):
            try:
                module = importlib.import_module(module_name)
            except (ImportError, RuntimeError, ValueError):
                continue
            inferred = self._infer_domain_vendor(module_name)
            if inferred is None:
                continue
            domain, vendor = inferred

            for _, klass in inspect.getmembers(module, inspect.isclass):
                if klass.__module__ != module.__name__:
                    continue
                if not klass.__name__.endswith("Connector"):
                    continue
                if inspect.isabstract(klass):
                    continue

                self.register(domain, vendor, klass, overwrite=True)
                discovered += 1
                break

        return discovered

    async def register_runtime(
        self,
        name: str,
        connector: Any,
        *,
        domain: str,
        vendor: str | None = None,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> None:
        """Register an instantiated runtime connector."""
        async with self._lock:
            if not overwrite and name in self._registrations:
                raise ValueError(f"Connector instance '{name}' is already registered")
            self._registrations[name] = ConnectorRegistration(
                name=name,
                connector=connector,
                domain=domain.strip().lower(),
                vendor=vendor.strip().lower() if vendor else None,
                metadata=metadata or {},
            )

    async def create(
        self,
        domain: str,
        *,
        vendor: str | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
        init_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Instantiate and register a connector class for *domain*/*vendor*."""
        normalized_domain = domain.strip().lower()
        selected_vendor = (
            (vendor or self.configured_vendor(normalized_domain) or "").strip().lower()
        )
        if not selected_vendor:
            raise ValueError(
                f"No provider configured for domain '{normalized_domain}'. "
                f"Set CONNECTOR_{normalized_domain.upper()}_PROVIDER or pass vendor explicitly."
            )

        definition = self.get_definition(normalized_domain, selected_vendor)
        if definition is None:
            raise ValueError(
                f"Unknown connector: {normalized_domain}:{selected_vendor}. "
                f"Run discovery and ensure the vendor is registered."
            )

        connector = definition.connector_class(**(init_kwargs or {}))
        runtime_name = name or f"{normalized_domain}:{selected_vendor}"
        await self.register_runtime(
            runtime_name,
            connector,
            domain=normalized_domain,
            vendor=selected_vendor,
            metadata=metadata,
            overwrite=overwrite,
        )
        return connector

    async def unregister(self, name: str) -> bool:
        """Unregister a runtime connector instance by name."""
        async with self._lock:
            removed = self._registrations.pop(name, None)
            self._health_cache.pop(name, None)
            return removed is not None

    async def get_runtime(self, name: str) -> Any | None:
        """Get a registered runtime connector instance by name."""
        async with self._lock:
            item = self._registrations.get(name)
            return item.connector if item else None

    async def list_registrations(self) -> list[ConnectorRegistration]:
        """List all runtime connector registrations."""
        async with self._lock:
            return list(self._registrations.values())

    async def list_domains(self) -> dict[str, list[str]]:
        """List runtime connector names grouped by domain."""
        async with self._lock:
            grouped: dict[str, list[str]] = {}
            for registration in self._registrations.values():
                grouped.setdefault(registration.domain, []).append(registration.name)
            for domain in grouped:
                grouped[domain].sort()
            return grouped

    async def count(self) -> int:
        """Return total number of runtime connector registrations."""
        async with self._lock:
            return len(self._registrations)

    async def health(self) -> dict[str, bool]:
        """Return health status for each runtime connector."""
        details = await self.health_details()
        return {name: item["ok"] for name, item in details.items()}

    async def health_details(self) -> dict[str, dict[str, Any]]:
        """Return detailed health data for each runtime connector."""
        registrations = await self.list_registrations()
        checks = await asyncio.gather(
            *(self._check_connector(item.connector) for item in registrations),
            return_exceptions=False,
        )
        details = {
            item.name: {
                "ok": health.ok,
                "checked_at": health.checked_at,
                "error": health.error,
                "details": health.details,
            }
            for item, health in zip(registrations, checks)
        }
        async with self._lock:
            for item, health in zip(registrations, checks):
                self._health_cache[item.name] = health
        return details

    async def start_health_monitor(self, interval_seconds: float = 60.0) -> None:
        """Start periodic health checks for runtime connectors."""
        async with self._lock:
            if self._monitor_task and not self._monitor_task.done():
                return
            interval = max(5.0, float(interval_seconds))
            self._monitor_task = asyncio.create_task(self._monitor_loop(interval))

    async def stop_health_monitor(self) -> None:
        """Stop periodic health checks."""
        async with self._lock:
            task = self._monitor_task
            self._monitor_task = None
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self, interval_seconds: float) -> None:
        while True:
            await self.health_details()
            await asyncio.sleep(interval_seconds)

    async def _check_connector(self, connector: Any) -> ConnectorHealth:
        now = datetime.now(timezone.utc).isoformat()
        health_method = getattr(connector, "health", None)
        details: dict[str, Any] = {}

        try:
            if health_method is None:
                ok = True
            else:
                result = health_method()
                if inspect.isawaitable(result):
                    result = await result
                if isinstance(result, dict):
                    details = dict(result)
                    ok = bool(result.get("ok", result.get("status") in {"ok", "healthy", True}))
                else:
                    ok = bool(result)

            if isinstance(connector, BaseAdapter):
                details["resilience"] = connector.resilience_status()

            return ConnectorHealth(ok=ok, checked_at=now, details=details)
        except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
            return ConnectorHealth(ok=False, checked_at=now, error=str(exc), details=details)

    @staticmethod
    def _infer_domain_vendor(module_name: str) -> tuple[str, str] | None:
        parts = module_name.split(".")
        try:
            idx = parts.index("connectors")
        except ValueError:
            return None

        relative = parts[idx + 1 :]
        if len(relative) < 3 or relative[-1] != "connector":
            return None

        domain_parts = relative[:-2]
        vendor = relative[-2]
        domain = "_".join(domain_parts)
        return domain.lower(), vendor.lower()


default_registry = ConnectorRegistry()
