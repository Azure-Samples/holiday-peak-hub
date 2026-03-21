"""Canonical pricing schemas.

Standardizes priced offers and aggregate pricing context so agents can reason
about promotions, channels, and effective ranges. Doctests show validation of
required fields and defaults.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PriceEntry(BaseModel):
    """A priced offer for a SKU, including discount context.

    >>> PriceEntry(sku="SKU-1", currency="USD", amount=10.0).amount
    10.0
    >>> PriceEntry(sku="SKU-1", currency="USD", amount=9.5, promotional=True).promotional
    True
    """

    sku: str
    currency: str
    amount: float
    list_amount: float | None = None
    discount_code: str | None = None
    channel: str | None = None
    region: str | None = None
    tax_included: bool = False
    promotional: bool = False
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class PriceContext(BaseModel):
    """Aggregate pricing view for agents.

    >>> offer = PriceEntry(sku="SKU-1", currency="USD", amount=8.0)
    >>> PriceContext(sku="SKU-1", active=offer, offers=[offer]).active.amount
    8.0
    """

    sku: str
    active: PriceEntry | None = None
    offers: list[PriceEntry] = Field(default_factory=list)
