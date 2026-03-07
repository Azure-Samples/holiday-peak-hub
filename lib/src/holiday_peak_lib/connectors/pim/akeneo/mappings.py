"""Data mappings from Akeneo PIM API responses to canonical models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from holiday_peak_lib.integrations.contracts import AssetData, ProductData


def _extract_value(
    values: dict,
    attribute: str,
    locale: str | None = None,
) -> Any:
    """Extract the first matching value from Akeneo's ``values`` structure.

    Akeneo stores each attribute as a list of ``{locale, scope, data}`` dicts.
    This helper returns the ``data`` field of the first entry that matches
    the given *locale*.  When *locale* is ``None``, returns the first entry
    whose locale is also ``None`` (i.e. non-localised attributes) or the first
    entry regardless.

    >>> vals = {"name": [{"locale": "en_US", "scope": None, "data": "Shirt"}]}
    >>> _extract_value(vals, "name", "en_US")
    'Shirt'
    >>> _extract_value(vals, "missing", "en_US") is None
    True
    """
    entries = values.get(attribute)
    if not entries:
        return None

    # Exact locale match first
    for entry in entries:
        if entry.get("locale") == locale:
            return entry.get("data")

    # Fallback: locale-agnostic (locale is None)
    for entry in entries:
        if entry.get("locale") is None:
            return entry.get("data")

    # Last resort: first available entry
    return entries[0].get("data") if entries else None


# Attribute keys that are explicitly mapped to ProductData fields
_MAPPED_ATTRIBUTES = {
    "name",
    "description",
    "short_description",
    "brand",
    "image",
}


def map_product(raw: dict, *, locale: str = "en_US") -> ProductData:
    """Map an Akeneo product response to a canonical ``ProductData``.

    >>> raw = {
    ...     "identifier": "SKU-001",
    ...     "categories": ["master", "shirts"],
    ...     "enabled": True,
    ...     "values": {
    ...         "name": [{"locale": "en_US", "scope": None, "data": "Casual Shirt"}],
    ...         "brand": [{"locale": None, "scope": None, "data": "Acme"}],
    ...     },
    ...     "updated": "2024-01-15T10:00:00+00:00",
    ... }
    >>> product = map_product(raw, locale="en_US")
    >>> product.sku
    'SKU-001'
    >>> product.title
    'Casual Shirt'
    >>> product.source_system
    'akeneo'
    """
    values = raw.get("values") or {}

    # Images: collect all entries for the "image" attribute
    image_entries = values.get("image") or []
    images = [entry.get("data") for entry in image_entries if entry.get("data")]

    # Variants from associations (UPSELL, X_SELL, etc.)
    variants: list[str] = []
    for assoc in (raw.get("associations") or {}).values():
        variants.extend(assoc.get("products", []))

    # Remaining attributes not explicitly mapped
    attributes: dict[str, Any] = {}
    for attr_key, attr_entries in values.items():
        if attr_key in _MAPPED_ATTRIBUTES:
            continue
        val = _extract_value(values, attr_key, locale)
        if val is not None:
            attributes[attr_key] = val

    # Parse last_modified
    last_modified: datetime | None = None
    updated_raw = raw.get("updated")
    if updated_raw:
        try:
            last_modified = datetime.fromisoformat(updated_raw)
        except ValueError:
            last_modified = None

    return ProductData(
        sku=raw.get("identifier", ""),
        title=_extract_value(values, "name", locale) or "",
        description=_extract_value(values, "description", locale),
        short_description=_extract_value(values, "short_description", locale),
        brand=_extract_value(values, "brand", locale),
        category_path=raw.get("categories") or [],
        attributes=attributes,
        images=images,
        variants=variants,
        status="active" if raw.get("enabled", True) else "inactive",
        source_system="akeneo",
        last_modified=last_modified,
    )


def map_asset(raw: dict) -> AssetData:
    """Map an Akeneo asset-manager record to a canonical ``AssetData``.

    >>> raw = {
    ...     "code": "asset-001",
    ...     "values": {
    ...         "media": [{"locale": None, "scope": None,
    ...             "data": {"filePath": "a/b/asset.jpg",
    ...                      "originalFilename": "product.jpg"}}],
    ...         "description": [{"locale": "en_US", "scope": None,
    ...             "data": "Product image"}],
    ...     },
    ... }
    >>> asset = map_asset(raw)
    >>> asset.id
    'asset-001'
    >>> asset.filename
    'product.jpg'
    """
    values = raw.get("values") or {}

    # Extract media info
    media_entries = values.get("media") or []
    media_data = media_entries[0].get("data", {}) if media_entries else {}

    file_path = ""
    filename = None
    if isinstance(media_data, dict):
        file_path = media_data.get("filePath", "")
        filename = media_data.get("originalFilename")
    elif isinstance(media_data, str):
        file_path = media_data
        filename = file_path.rsplit("/", 1)[-1] if file_path else None

    # Derive content type from filename extension
    content_type = "application/octet-stream"
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        _ext_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "svg": "image/svg+xml",
            "pdf": "application/pdf",
            "mp4": "video/mp4",
        }
        content_type = _ext_map.get(ext, content_type)

    description = _extract_value(values, "description", "en_US")

    return AssetData(
        id=raw.get("code", ""),
        url=file_path,
        content_type=content_type,
        filename=filename,
        alt_text=description,
    )
