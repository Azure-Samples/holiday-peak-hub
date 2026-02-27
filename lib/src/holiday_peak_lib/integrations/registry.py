"""Connector registry for runtime connector discovery and access."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ConnectorRegistration:
    """Runtime metadata for a registered connector."""

    name: str
    connector: Any
    domain: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ConnectorRegistry:
    """In-memory connector registry used by services and agents.

    The registry is intentionally lightweight and can be injected via
    ``build_service_app(..., connector_registry=...)``.
    """

    def __init__(self) -> None:
        self._registrations: dict[str, ConnectorRegistration] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        name: str,
        connector: Any,
        *,
        domain: str | None = None,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> None:
        async with self._lock:
            if not overwrite and name in self._registrations:
                raise ValueError(f"Connector '{name}' is already registered")
            self._registrations[name] = ConnectorRegistration(
                name=name,
                connector=connector,
                domain=domain,
                metadata=metadata or {},
            )

    async def unregister(self, name: str) -> bool:
        async with self._lock:
            return self._registrations.pop(name, None) is not None

    async def get(self, name: str) -> Any | None:
        async with self._lock:
            registration = self._registrations.get(name)
            return registration.connector if registration else None

    async def list_registrations(self) -> list[ConnectorRegistration]:
        async with self._lock:
            return list(self._registrations.values())

    async def list_domains(self) -> dict[str, list[str]]:
        async with self._lock:
            domains: dict[str, list[str]] = {}
            for item in self._registrations.values():
                key = item.domain or "unclassified"
                domains.setdefault(key, []).append(item.name)
            return domains

    async def count(self) -> int:
        async with self._lock:
            return len(self._registrations)

    async def health(self) -> dict[str, bool]:
        registrations = await self.list_registrations()
        checks = await asyncio.gather(
            *(self._check_connector(item.connector) for item in registrations),
            return_exceptions=False,
        )
        return {item.name: check for item, check in zip(registrations, checks)}

    async def _check_connector(self, connector: Any) -> bool:
        health_method = getattr(connector, "health", None)
        if health_method is None:
            return True
        try:
            result = health_method()
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, dict):
                return bool(result.get("ok", True))
            return bool(result)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return False
