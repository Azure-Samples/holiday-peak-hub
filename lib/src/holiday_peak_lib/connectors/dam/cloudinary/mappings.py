"""Data mappings from Cloudinary Admin API responses to canonical ``AssetData``."""

from __future__ import annotations

from holiday_peak_lib.integrations.contracts import AssetData

# Cloudinary resource_type + format → MIME content type
_MIME_MAP: dict[str, str] = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "ico": "image/x-icon",
    "mp4": "video/mp4",
    "webm": "video/webm",
    "mov": "video/quicktime",
    "avi": "video/x-msvideo",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "pdf": "application/pdf",
}

_RESOURCE_TYPE_PREFIX: dict[str, str] = {
    "image": "image",
    "video": "video",
    "raw": "application",
}


def _derive_content_type(resource_type: str, fmt: str) -> str:
    """Derive a MIME content type from Cloudinary ``resource_type`` and ``format``."""
    if fmt in _MIME_MAP:
        return _MIME_MAP[fmt]
    prefix = _RESOURCE_TYPE_PREFIX.get(resource_type, "application")
    return f"{prefix}/{fmt}" if fmt else f"{prefix}/octet-stream"


def map_resource(raw: dict) -> AssetData:
    """Map a Cloudinary Admin API resource dict to a canonical ``AssetData``.

    >>> raw = {
    ...     "public_id": "sample/image1",
    ...     "format": "jpg",
    ...     "resource_type": "image",
    ...     "url": "http://res.cloudinary.com/demo/image/upload/sample/image1.jpg",
    ...     "secure_url": "https://res.cloudinary.com/demo/image/upload/sample/image1.jpg",
    ...     "bytes": 120453,
    ...     "width": 1200,
    ...     "height": 800,
    ...     "tags": ["product", "lifestyle"],
    ...     "context": {"custom": {"alt": "Product shot"}},
    ... }
    >>> asset = map_resource(raw)
    >>> asset.id
    'sample/image1'
    >>> asset.content_type
    'image/jpeg'
    >>> asset.alt_text
    'Product shot'
    """
    public_id = raw.get("public_id", "")
    fmt = raw.get("format", "")
    resource_type = raw.get("resource_type", "image")

    # Filename = last segment of public_id + extension
    filename_base = public_id.rsplit("/", 1)[-1] if public_id else ""
    filename = f"{filename_base}.{fmt}" if filename_base and fmt else filename_base or None

    # Alt text from context.custom.alt
    context = raw.get("context") or {}
    custom = context.get("custom") or {}
    alt_text = custom.get("alt")

    # Fields that are directly mapped
    _mapped_keys = {
        "public_id",
        "format",
        "resource_type",
        "url",
        "secure_url",
        "bytes",
        "width",
        "height",
        "tags",
        "context",
    }
    metadata = {k: v for k, v in raw.items() if k not in _mapped_keys}

    return AssetData(
        id=public_id,
        url=raw.get("secure_url") or raw.get("url", ""),
        content_type=_derive_content_type(resource_type, fmt),
        filename=filename,
        size_bytes=raw.get("bytes"),
        width=raw.get("width"),
        height=raw.get("height"),
        alt_text=alt_text,
        tags=raw.get("tags") or [],
        metadata=metadata,
    )
