"""Protocol versioning and interface evolution for enterprise connectors.

Provides mechanisms for:

- Declaring versioned connector protocols with typed field specifications.
- Registering and negotiating compatible protocol versions between a client
  and a server without breaking changes.
- Wrapping concrete adapters with :class:`VersionedAdapter` so that a newer
  implementation can serve an older client by masking unknown fields.
- Emitting deprecation warnings when outdated protocol versions are used.
- Computing diffs between two protocol versions to aid migration planning.

Usage example::

    from holiday_peak_lib.connectors.common.versioning import (
        ProtocolVersion,
        PIMConnectorProtocol_v1,
        PIMConnectorProtocol_v2,
        VersionedAdapter,
        diff_protocols,
        negotiate_version,
    )

    # Negotiate which version to use
    protocol_class = negotiate_version("pim", ProtocolVersion(1, 0))

    # Wrap a v2 connector to serve a v1 client
    adapter = VersionedAdapter(
        my_pim_v2_connector,
        protocol_class=PIMConnectorProtocol_v2,
        client_version=ProtocolVersion(1, 0),
    )
    product = await adapter.get_product("P-001")  # returns v1-shaped dict

    # Plan a migration
    diff = diff_protocols(PIMConnectorProtocol_v1, PIMConnectorProtocol_v2)
    print(diff.summary())
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ProtocolVersion
# ---------------------------------------------------------------------------


class ProtocolVersion:
    """Comparable semantic version for connector protocols (major.minor).

    Compatibility is defined as equal major versions.  A client at ``v1.0``
    is compatible with a server at ``v1.2``, but NOT with ``v2.0``.

    >>> ProtocolVersion(1, 0) < ProtocolVersion(2, 0)
    True
    >>> ProtocolVersion(1, 0).is_compatible_with(ProtocolVersion(1, 5))
    True
    >>> ProtocolVersion(1, 0).is_compatible_with(ProtocolVersion(2, 0))
    False
    """

    __slots__ = ("major", "minor")

    def __init__(self, major: int, minor: int = 0) -> None:
        if major < 0 or minor < 0:
            raise ValueError("Protocol version numbers must be non-negative integers")
        self.major = major
        self.minor = minor

    def __str__(self) -> str:
        return f"v{self.major}.{self.minor}"

    def __repr__(self) -> str:
        return f"ProtocolVersion({self.major}, {self.minor})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProtocolVersion):
            return NotImplemented
        return self.major == other.major and self.minor == other.minor

    def __lt__(self, other: "ProtocolVersion") -> bool:
        return (self.major, self.minor) < (other.major, other.minor)

    def __le__(self, other: "ProtocolVersion") -> bool:
        return self == other or self < other

    def __gt__(self, other: "ProtocolVersion") -> bool:
        return not self <= other

    def __ge__(self, other: "ProtocolVersion") -> bool:
        return not self < other

    def __hash__(self) -> int:
        return hash((self.major, self.minor))

    def is_compatible_with(self, other: "ProtocolVersion") -> bool:
        """Return True when major versions match (minor changes are backward-compatible)."""
        return self.major == other.major


# ---------------------------------------------------------------------------
# Field specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    """Specification of a single named field in a versioned protocol.

    Attributes:
        name: Canonical field name in the protocol payload.
        type_hint: Human-readable type annotation (for documentation/diffing).
        required: Whether this field must be present in every response.
        deprecated: When True the field should not be used in new integrations.
        added_in: Protocol version that introduced this field (None = v1.0).
        removed_in: Protocol version that will remove this field (None = not removed).
    """

    name: str
    type_hint: str
    required: bool = True
    deprecated: bool = False
    added_in: ProtocolVersion | None = None
    removed_in: ProtocolVersion | None = None


# ---------------------------------------------------------------------------
# Protocol diff
# ---------------------------------------------------------------------------


@dataclass
class ProtocolDiff:
    """Result of comparing two protocol versions.

    Attributes:
        added: Field names present in the newer version but not the older.
        removed: Field names present in the older version but not the newer.
        deprecated: Field names marked deprecated in the newer version.
    """

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    deprecated: list[str] = field(default_factory=list)

    def is_breaking(self) -> bool:
        """Return True when the diff contains removed (breaking) fields."""
        return bool(self.removed)

    def summary(self) -> str:
        """Return a human-readable one-line description of the diff."""
        parts = []
        if self.added:
            parts.append(f"+{len(self.added)} added")
        if self.removed:
            parts.append(f"-{len(self.removed)} removed (breaking)")
        if self.deprecated:
            parts.append(f"~{len(self.deprecated)} deprecated")
        return ", ".join(parts) if parts else "no changes"


# ---------------------------------------------------------------------------
# BaseConnectorProtocol metaclass + ABC
# ---------------------------------------------------------------------------


class _ProtocolMeta(type(ABC)):
    """Metaclass that validates VERSION type on protocol class creation."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
    ) -> "_ProtocolMeta":
        cls = super().__new__(mcs, name, bases, namespace)
        version = namespace.get("VERSION")
        if version is not None and not isinstance(version, ProtocolVersion):
            raise TypeError(
                f"{name}.VERSION must be a ProtocolVersion instance, got {type(version)!r}"
            )
        return cls


class BaseConnectorProtocol(ABC, metaclass=_ProtocolMeta):
    """Abstract base for versioned connector protocol classes.

    Subclasses must declare a ``VERSION`` class attribute and should populate
    ``FIELDS`` to enable diff and migration tooling.  Set ``DEPRECATED = True``
    on a protocol class to signal that all consumers should migrate.
    """

    VERSION: ClassVar[ProtocolVersion]
    FIELDS: ClassVar[list[FieldSpec]] = []
    DEPRECATED: ClassVar[bool] = False


# ---------------------------------------------------------------------------
# PIM protocol — v1
# ---------------------------------------------------------------------------


class PIMConnectorProtocol_v1(BaseConnectorProtocol):  # pylint: disable=invalid-name
    """PIM connector protocol v1 — baseline product data operations.

    Provides fundamental read operations against any product information
    management system: fetching a single product and paginated product listings.
    All vendors implementing a PIM integration must satisfy this interface.

    Upgrade path: see :class:`PIMConnectorProtocol_v2` for extended capabilities.
    """

    VERSION = ProtocolVersion(1, 0)
    FIELDS: ClassVar[list[FieldSpec]] = [
        FieldSpec("product_id", "str"),
        FieldSpec("name", "str"),
        FieldSpec("description", "Optional[str]", required=False),
        FieldSpec("sku", "Optional[str]", required=False),
        FieldSpec("category", "Optional[str]", required=False),
        FieldSpec("price", "Optional[float]", required=False),
        FieldSpec("images", "list[str]", required=False),
        FieldSpec("attributes", "dict", required=False),
    ]

    @abstractmethod
    async def get_product(self, product_id: str) -> dict[str, Any]:
        """Fetch a single product by its canonical identifier."""

    @abstractmethod
    async def list_products(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch a paginated slice of products from the PIM."""


# ---------------------------------------------------------------------------
# PIM protocol — v2
# ---------------------------------------------------------------------------


class PIMConnectorProtocol_v2(PIMConnectorProtocol_v1):  # pylint: disable=invalid-name
    """PIM connector protocol v2 — adds lifecycle, variants, and keyword search.

    v2 is backward-compatible with v1 (same major version).  All v1 methods
    continue to work unchanged; new additions are strictly additive.

    New capabilities:
    - ``get_product_variants``: fetch color/size/material variants for a base product.
    - ``search_products``: keyword or semantic search path.
    - Additional optional fields on product payloads: ``taxonomy_path``,
      ``extended_attrs``, ``variants``, ``rich_text_blocks``, ``lifecycle_status``.

    Migration from v1 to v2: no breaking changes — just start using the new
    methods and consume the additional optional fields as needed.
    """

    VERSION = ProtocolVersion(2, 0)
    FIELDS: ClassVar[list[FieldSpec]] = PIMConnectorProtocol_v1.FIELDS + [
        FieldSpec(
            "taxonomy_path",
            "list[str]",
            required=False,
            added_in=ProtocolVersion(2, 0),
        ),
        FieldSpec(
            "extended_attrs",
            "dict[str, Any]",
            required=False,
            added_in=ProtocolVersion(2, 0),
        ),
        FieldSpec(
            "variants",
            "list[dict]",
            required=False,
            added_in=ProtocolVersion(2, 0),
        ),
        FieldSpec(
            "rich_text_blocks",
            "list[dict]",
            required=False,
            added_in=ProtocolVersion(2, 0),
        ),
        FieldSpec(
            "lifecycle_status",
            "Optional[str]",
            required=False,
            added_in=ProtocolVersion(2, 0),
        ),
    ]

    @abstractmethod
    async def get_product_variants(self, product_id: str) -> list[dict[str, Any]]:
        """Fetch variants (color, size, material, etc.) for a base product."""

    @abstractmethod
    async def search_products(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search products by keyword or semantic query string."""


# ---------------------------------------------------------------------------
# Protocol registry
# ---------------------------------------------------------------------------

_PROTOCOL_REGISTRY: dict[str, list[type[BaseConnectorProtocol]]] = {}


def register_protocol(family: str, protocol: type[BaseConnectorProtocol]) -> None:
    """Register a versioned protocol class under a named family.

    Args:
        family: Domain family name (e.g. ``"pim"``, ``"crm"``).
        protocol: A :class:`BaseConnectorProtocol` subclass with a ``VERSION`` attribute.

    >>> register_protocol("test", PIMConnectorProtocol_v1)
    """
    _PROTOCOL_REGISTRY.setdefault(family, []).append(protocol)


def negotiate_version(
    family: str,
    requested: ProtocolVersion,
) -> type[BaseConnectorProtocol] | None:
    """Return the best registered protocol version compatible with *requested*.

    Selects the newest registered version whose major version equals
    *requested.major* and whose minor version is ≤ *requested.minor*, so the
    server can satisfy the client's contract without breaking changes.

    Args:
        family: Protocol family name (e.g. ``"pim"``).
        requested: The protocol version the client requires.

    Returns:
        The matching protocol class, or ``None`` when no compatible version is
        registered.

    >>> cls = negotiate_version("pim", ProtocolVersion(1, 0))
    >>> cls is PIMConnectorProtocol_v1
    True
    >>> negotiate_version("pim", ProtocolVersion(2, 0)) is PIMConnectorProtocol_v2
    True
    >>> negotiate_version("pim", ProtocolVersion(99, 0)) is None
    True
    """
    candidates = _PROTOCOL_REGISTRY.get(family, [])
    compatible = [
        p
        for p in candidates
        if hasattr(p, "VERSION")
        and p.VERSION.is_compatible_with(requested)
        and p.VERSION <= requested
    ]
    if not compatible:
        return None
    return max(compatible, key=lambda p: p.VERSION)


# Register the built-in PIM protocol versions.
register_protocol("pim", PIMConnectorProtocol_v1)
register_protocol("pim", PIMConnectorProtocol_v2)


# ---------------------------------------------------------------------------
# VersionedAdapter
# ---------------------------------------------------------------------------


class VersionedAdapter:
    """Wraps a concrete connector to expose it under a specific protocol version.

    When a connector implements a *newer* protocol but a client requests an
    *older* version, ``VersionedAdapter`` strips fields that were not present
    in the requested version.  If the client version is lower than the server
    version a deprecation warning is logged to encourage upgrades.

    All public connector methods are accessible directly via attribute
    delegation.  For the core PIM methods (``get_product``, ``list_products``)
    the adapter applies the version mask automatically::

        connector = MyPIMV2Connector()           # implements v2
        adapter = VersionedAdapter(
            connector,
            protocol_class=PIMConnectorProtocol_v2,
            client_version=ProtocolVersion(1, 0),
        )
        product = await adapter.get_product("P-001")
        # No v2-only fields (taxonomy_path, variants, …) in the result.
    """

    def __init__(
        self,
        connector: Any,
        *,
        protocol_class: type[BaseConnectorProtocol],
        client_version: ProtocolVersion | None = None,
    ) -> None:
        self._connector = connector
        self._protocol_class = protocol_class
        self._server_version: ProtocolVersion | None = getattr(protocol_class, "VERSION", None)
        self._client_version = client_version or self._server_version

        if (
            self._client_version is not None
            and self._server_version is not None
            and self._client_version < self._server_version
        ):
            logger.warning(
                "Client is requesting protocol version %s but server provides %s "
                "for '%s'. Consider upgrading the client to take advantage of "
                "newer capabilities.",
                self._client_version,
                self._server_version,
                protocol_class.__name__,
            )

        if getattr(protocol_class, "DEPRECATED", False):
            logger.warning(
                "Protocol class '%s' is marked as deprecated. "
                "Migrate to a newer version as soon as possible.",
                protocol_class.__name__,
            )

    # ------------------------------------------------------------------
    # Attribute delegation
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connector, name)

    # ------------------------------------------------------------------
    # Version masking helpers
    # ------------------------------------------------------------------

    def _fields_for_version(self, version: ProtocolVersion) -> set[str]:
        """Return the set of field names available at *version*."""
        fields: set[str] = set()
        for cls in reversed(type.mro(self._protocol_class)):
            if not (isinstance(cls, type) and issubclass(cls, BaseConnectorProtocol)):
                continue
            for f in getattr(cls, "FIELDS", []):
                introduced = f.added_in or ProtocolVersion(1, 0)
                if introduced <= version:
                    fields.add(f.name)
        return fields

    def _all_protocol_fields(self) -> set[str]:
        """Return all field names defined across all versions of this protocol."""
        fields: set[str] = set()
        for cls in type.mro(self._protocol_class):
            if isinstance(cls, type) and issubclass(cls, BaseConnectorProtocol):
                for f in getattr(cls, "FIELDS", []):
                    fields.add(f.name)
        return fields

    def _apply_version_mask(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove fields unknown to the client's requested version.

        Fields that are not part of *any* protocol version (e.g. internal
        connector state keys) are kept as-is.
        """
        if self._client_version is None or self._server_version is None:
            return data
        if self._client_version >= self._server_version:
            return data

        known_at_client = self._fields_for_version(self._client_version)
        all_protocol = self._all_protocol_fields()
        return {k: v for k, v in data.items() if k in known_at_client or k not in all_protocol}

    # ------------------------------------------------------------------
    # Core PIM method delegates with version masking
    # ------------------------------------------------------------------

    async def get_product(self, product_id: str) -> dict[str, Any]:
        """Delegate and apply version mask to the returned product payload."""
        data: dict[str, Any] = await self._connector.get_product(product_id)
        return self._apply_version_mask(data)

    async def list_products(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Delegate and apply version mask to each product in the listing."""
        items: list[dict[str, Any]] = await self._connector.list_products(
            limit=limit,
            offset=offset,
        )
        return [self._apply_version_mask(item) for item in items]


# ---------------------------------------------------------------------------
# Migration helper
# ---------------------------------------------------------------------------


def diff_protocols(
    from_version: type[BaseConnectorProtocol],
    to_version: type[BaseConnectorProtocol],
) -> ProtocolDiff:
    """Compute the field-level diff between two protocol version classes.

    Args:
        from_version: The older (source) protocol class.
        to_version: The newer (target) protocol class.

    Returns:
        A :class:`ProtocolDiff` describing added, removed, and deprecated fields.

    Raises:
        TypeError: When either argument is not a :class:`BaseConnectorProtocol` subclass.

    >>> diff = diff_protocols(PIMConnectorProtocol_v1, PIMConnectorProtocol_v2)
    >>> len(diff.added) > 0
    True
    >>> diff.is_breaking()
    False
    >>> diff.summary()
    '+5 added'
    """
    for arg, label in ((from_version, "from_version"), (to_version, "to_version")):
        if not (isinstance(arg, type) and issubclass(arg, BaseConnectorProtocol)):
            raise TypeError(f"{label} must be a BaseConnectorProtocol subclass, got {arg!r}")

    from_fields = {f.name: f for f in getattr(from_version, "FIELDS", [])}
    to_fields = {f.name: f for f in getattr(to_version, "FIELDS", [])}

    added = [name for name in to_fields if name not in from_fields]
    removed = [name for name in from_fields if name not in to_fields]
    deprecated = [name for name, f in to_fields.items() if f.deprecated and name not in removed]

    return ProtocolDiff(added=added, removed=removed, deprecated=deprecated)
