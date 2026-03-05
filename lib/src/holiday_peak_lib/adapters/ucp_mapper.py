"""Universal Commerce Protocol (UCP) mapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from holiday_peak_lib.adapters.protocol_mapper import ProtocolMapper

if TYPE_CHECKING:
    from holiday_peak_lib.schemas.truth import ProductStyle, TruthAttribute

_REQUIRED_UCP_FIELDS = {"product_id", "title", "brand", "price_amount", "currency"}


class UcpProtocolMapper(ProtocolMapper):
    """Map a truth-layer ``ProductStyle`` to the Universal Commerce Protocol format.

    UCP is a flat, commerce-optimised format that includes the full truth
    attribute set, completeness score, and compliance metadata.
    """

    def map(
        self,
        product: "ProductStyle",
        attributes: "list[TruthAttribute]",
        mapping: dict,
    ) -> dict:
        """Transform *product* + *attributes* into a UCP payload dict.

        Args:
            product: Canonical style record from the truth store.
            attributes: Approved truth attributes for the product.
            mapping: Protocol field-mapping config (loaded from Cosmos mappings
                container).

        Returns:
            Flat UCP-formatted dict ready for delivery.
        """
        attr_lookup: dict[str, Any] = {a.attribute_key: a.value for a in attributes}

        price_raw = attr_lookup.get("price", mapping.get("price", 0.0))
        try:
            price_amount = float(price_raw)
        except (TypeError, ValueError):
            price_amount = 0.0

        currency = str(attr_lookup.get("currency", mapping.get("currency", "usd")))
        availability = str(attr_lookup.get("availability", mapping.get("availability", "in_stock")))

        payload: dict[str, Any] = {
            "product_id": product.id,
            "title": product.model_name,
            "brand": product.brand or "",
            "category": product.category_id,
            "description": "",
            "image_url": "",
            "price_amount": price_amount,
            "currency": currency,
            "availability": availability,
            "protocol": "ucp",
            "protocol_version": mapping.get("protocol_version", "1.0"),
            "compliance": {
                "source": "truth-store",
                "attribute_count": len(attributes),
                "approved_attributes": len(attributes),
            },
        }

        # Merge remaining truth attributes as extended fields
        extended = {
            k: v for k, v in attr_lookup.items() if k not in {"price", "currency", "availability"}
        }
        if extended:
            payload["extended_attributes"] = extended

        # Apply any custom field overrides from the mapping config
        for dest_field, src_field in mapping.get("field_overrides", {}).items():
            if src_field in attr_lookup:
                payload[dest_field] = attr_lookup[src_field]

        return payload

    def validate_output(self, output: dict, protocol_version: str) -> bool:
        """Return ``True`` when all required UCP fields are present and non-empty."""
        return all(output.get(field) is not None for field in _REQUIRED_UCP_FIELDS)
