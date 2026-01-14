"""Canonical pricing schemas.

Standardizes priced offers and aggregate pricing context so agents can reason
about promotions, channels, and effective ranges. Doctests show validation of
required fields and defaults.
"""

from datetime import datetime
from typing import Any, Optional

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
    list_amount: Optional[float] = None
    discount_code: Optional[str] = None
    channel: Optional[str] = None
    region: Optional[str] = None
    tax_included: bool = False
    promotional: bool = False
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class PriceContext(BaseModel):
    """Aggregate pricing view for agents.

    >>> offer = PriceEntry(sku="SKU-1", currency="USD", amount=8.0)
    >>> PriceContext(sku="SKU-1", active=offer, offers=[offer]).active.amount
    8.0
    """

    sku: str
    active: Optional[PriceEntry] = None
    offers: list[PriceEntry] = Field(default_factory=list)
