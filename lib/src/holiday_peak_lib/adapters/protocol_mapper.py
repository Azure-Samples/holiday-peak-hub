"""Abstract base class for protocol mappers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from holiday_peak_lib.schemas.truth import ProductStyle, TruthAttribute


class ProtocolMapper(ABC):
    """Abstract base for all protocol-specific product mappers.

    Concrete implementations transform canonical ``ProductStyle`` records and
    their associated ``TruthAttribute`` list into the wire format expected by a
    downstream trading partner or commerce protocol.
    """

    @abstractmethod
    def map(
        self,
        product: "ProductStyle",
        attributes: "list[TruthAttribute]",
        mapping: dict,
    ) -> dict:
        """Transform *product* + *attributes* into the protocol-specific payload.

        Args:
            product: Canonical style record from the truth store.
            attributes: Approved truth attributes for the product.
            mapping: Protocol field-mapping configuration loaded from Cosmos.

        Returns:
            A dictionary ready for serialisation / delivery.
        """

    @abstractmethod
    def validate_output(self, output: dict, protocol_version: str) -> bool:
        """Return ``True`` if *output* satisfies the protocol schema.

        Args:
            output: The mapped payload produced by :meth:`map`.
            protocol_version: Semver-style version string (e.g. ``"1.0"``).

        Returns:
            ``True`` when the output is valid for the given protocol version.
        """
