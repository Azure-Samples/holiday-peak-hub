"""Correlation ID context utilities for request-scoped tracing."""

from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

CORRELATION_HEADER = "x-correlation-id"

_CORRELATION_ID_CTX: ContextVar[str] = ContextVar("holiday_peak_correlation_id", default="")


def _normalize_correlation_id(correlation_id: str | None) -> str:
    value = (correlation_id or "").strip()
    if value:
        return value
    return str(uuid4())


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set request correlation ID in context and return the resolved value."""
    resolved = _normalize_correlation_id(correlation_id)
    _CORRELATION_ID_CTX.set(resolved)
    return resolved


def get_correlation_id() -> str | None:
    """Return current correlation ID from context (if any)."""
    value = _CORRELATION_ID_CTX.get().strip()
    return value or None


def clear_correlation_id() -> None:
    """Clear correlation ID from context."""
    _CORRELATION_ID_CTX.set("")
