"""Data mappings from Salsify API responses to canonical ``ProductData`` models."""

from __future__ import annotations

from datetime import datetime

from holiday_peak_lib.integrations.contracts import AssetData, ProductData


def map_product(raw: dict) -> ProductData:
    """Map a Salsify product record to a canonical ``ProductData``.

    Salsify products are represented as flat dictionaries whose keys may use
    Salsify property IDs.  The mapping normalises the most common well-known
    fields; all remaining attributes are preserved in ``attributes``.

    >>> from datetime import datetime, timezone
    >>> raw = {
    ...     "salsify:id": "sku-001",
    ...     "Product Name": "Widget",
    ...     "Product Description": "A fine widget",
    ...     "Brand": "Acme",
    ...     "salsify:updated_at": "2024-01-15T10:00:00Z",
    ... }
    >>> product = map_product(raw)
    >>> product.sku
    'sku-001'
    >>> product.title
    'Widget'
    >>> product.brand
    'Acme'
    >>> product.source_system
    'salsify'
    """
    known_keys = {
        "salsify:id",
        "Product Name",
        "Product Description",
        "Short Description",
        "Brand",
        "salsify:updated_at",
        "salsify:digital_assets",
        "Product Status",
        "salsify:relations",
    }

    attributes = {k: v for k, v in raw.items() if k not in known_keys}

    updated_raw = raw.get("salsify:updated_at")
    last_modified: datetime | None = None
    if updated_raw:
        try:
            last_modified = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
        except ValueError:
            last_modified = None

    images = [
        a.get("salsify:url", "")
        for a in raw.get("salsify:digital_assets", [])
        if a.get("salsify:url")
    ]

    variants = [
        r.get("salsify:id", "") for r in raw.get("salsify:relations", []) if r.get("salsify:id")
    ]

    return ProductData(
        sku=raw.get("salsify:id", ""),
        title=raw.get("Product Name", ""),
        description=raw.get("Product Description"),
        short_description=raw.get("Short Description"),
        brand=raw.get("Brand"),
        attributes=attributes,
        images=images,
        variants=variants,
        status=raw.get("Product Status", "active"),
        source_system="salsify",
        last_modified=last_modified,
    )


def map_asset(raw: dict) -> AssetData:
    """Map a Salsify digital asset record to canonical ``AssetData``.

    >>> raw = {
    ...     "salsify:id": "asset-1",
    ...     "salsify:url": "https://cdn.salsify.com/images/asset-1.jpg",
    ...     "salsify:content_type": "image/jpeg",
    ...     "salsify:filename": "product.jpg",
    ... }
    >>> asset = map_asset(raw)
    >>> asset.id
    'asset-1'
    >>> asset.content_type
    'image/jpeg'
    """
    return AssetData(
        id=raw.get("salsify:id", ""),
        url=raw.get("salsify:url", ""),
        content_type=raw.get("salsify:content_type", "application/octet-stream"),
        filename=raw.get("salsify:filename"),
        size_bytes=raw.get("salsify:size"),
        width=raw.get("salsify:width"),
        height=raw.get("salsify:height"),
        alt_text=raw.get("salsify:name"),
        tags=raw.get("salsify:tags", []),
        metadata={k: v for k, v in raw.items() if not k.startswith("salsify:")},
    )
