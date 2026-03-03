"""Shared ACP mapping utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from holiday_peak_lib.adapters.protocol_mapper import ProtocolMapper
from holiday_peak_lib.schemas.acp import AcpPartnerProfile, AcpProduct
from holiday_peak_lib.schemas.product import CatalogProduct

if TYPE_CHECKING:
    from holiday_peak_lib.schemas.truth import ProductStyle, TruthAttribute

_REQUIRED_ACP_FIELDS = {"item_id", "title", "description", "url", "image_url", "brand", "price"}


class AcpCatalogMapper(ProtocolMapper):
    """Map catalog products and truth-layer styles to ACP Product Feed fields."""

    # ------------------------------------------------------------------
    # ProtocolMapper abstract interface
    # ------------------------------------------------------------------

    def map(
        self,
        product: "ProductStyle",
        attributes: "list[TruthAttribute]",
        mapping: dict,
    ) -> dict:
        """Transform a truth-layer ``ProductStyle`` into an ACP payload.

        Uses *mapping* to resolve field aliases and *attributes* to populate
        extended fields.  Partner policy filtering is delegated to
        :meth:`apply_partner_policy`.
        """
        attr_lookup: dict[str, Any] = {a.field_name: a.value for a in attributes}
        price_raw = attr_lookup.get("price", mapping.get("price", 0.0))
        try:
            price_val = float(price_raw)
        except (TypeError, ValueError):
            price_val = 0.0
        currency = str(attr_lookup.get("currency", mapping.get("currency", "usd")))
        availability = str(attr_lookup.get("availability", mapping.get("availability", "in_stock")))
        sku = mapping.get("item_id_field", "style_id")
        item_id = getattr(product, sku, product.style_id)

        acp = AcpProduct(
            item_id=str(item_id),
            title=product.name,
            description=product.description or "",
            url=f"https://example.com/products/{item_id}",
            image_url=product.image_url or "https://example.com/images/placeholder.png",
            brand=product.brand or "",
            price=f"{price_val:.2f} {currency}",
            availability=availability,
            protocol_version=mapping.get("protocol_version", "1.0"),
            extended_attributes={
                k: v
                for k, v in attr_lookup.items()
                if k not in {"price", "currency", "availability"}
            },
        )
        return acp.model_dump()

    def validate_output(self, output: dict, protocol_version: str) -> bool:
        """Return ``True`` when all required ACP fields are present and non-empty."""
        return all(output.get(field) for field in _REQUIRED_ACP_FIELDS)

    # ------------------------------------------------------------------
    # Legacy helper (used by existing catalog services)
    # ------------------------------------------------------------------

    def to_acp_product(
        self,
        product: CatalogProduct,
        *,
        availability: str,
        currency: str = "usd",
        partner_profile: AcpPartnerProfile | None = None,
    ) -> dict[str, Any]:
        """Map a :class:`CatalogProduct` to an ACP payload dict."""
        sku = product.sku
        price = product.price if product.price is not None else 0.0
        image_url = product.image_url or "https://example.com/images/placeholder.png"
        product_url = f"https://example.com/products/{sku}"
        acp = AcpProduct(
            item_id=sku,
            title=product.name,
            description=product.description or "",
            url=product_url,
            image_url=image_url,
            brand=product.brand or "",
            price=f"{price:.2f} {currency}",
            availability=availability,
            partner_profile=partner_profile,
        )
        result = acp.model_dump()
        if partner_profile:
            result = self.apply_partner_policy(result, partner_profile)
        return result

    # ------------------------------------------------------------------
    # Partner policy filtering
    # ------------------------------------------------------------------

    def apply_partner_policy(
        self, payload: dict[str, Any], partner_profile: AcpPartnerProfile
    ) -> dict[str, Any]:
        """Strip *restricted_fields* from *payload* per the partner's share policy."""
        filtered = dict(payload)
        for field in partner_profile.restricted_fields:
            filtered.pop(field, None)
        return filtered
