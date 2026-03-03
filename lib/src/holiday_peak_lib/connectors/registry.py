"""Connector registry for discovering and managing enterprise connectors."""

from typing import Optional, Type


class ConnectorRegistry:
    """Central registry for all enterprise connector classes.

    Connectors register themselves by domain and vendor name and can be looked
    up at runtime to instantiate the appropriate integration.

    >>> registry = ConnectorRegistry()
    >>> class DummyConnector:
    ...     pass
    >>> registry.register("pim", "dummy", DummyConnector)
    >>> registry.get("pim", "dummy") is DummyConnector
    True
    >>> registry.get("pim", "unknown") is None
    True
    """

    def __init__(self) -> None:
        self._registry: dict[str, dict[str, Type]] = {}

    def register(self, domain: str, vendor: str, connector_class: Type) -> None:
        """Register a connector class under the given domain and vendor key."""
        self._registry.setdefault(domain, {})[vendor] = connector_class

    def get(self, domain: str, vendor: str) -> Optional[Type]:
        """Return the connector class for the given domain and vendor, or None."""
        return self._registry.get(domain, {}).get(vendor)

    def list_vendors(self, domain: str) -> list[str]:
        """List registered vendor keys for a domain.

        >>> registry = ConnectorRegistry()
        >>> registry.register("pim", "salsify", object)
        >>> registry.list_vendors("pim")
        ['salsify']
        """
        return list(self._registry.get(domain, {}).keys())


#: Global default registry instance.
default_registry = ConnectorRegistry()
