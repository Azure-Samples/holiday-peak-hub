"""Canonical logistics schemas.

Defines shipment and event representations used by agents for tracking and
exception handling as described in the business summary. Doctests show basic
construction.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ShipmentEvent(BaseModel):
    """Timeline event for a shipment.

    >>> from datetime import datetime
    >>> ShipmentEvent(code="PU", occurred_at=datetime(2024, 1, 1)).code
    'PU'
    """

    code: str
    description: Optional[str] = None
    occurred_at: datetime
    location: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class Shipment(BaseModel):
    """Normalized shipment status.

    >>> Shipment(tracking_id="T1", status="in_transit").tracking_id
    'T1'
    """

    tracking_id: str
    order_id: Optional[str] = None
    carrier: Optional[str] = None
    status: str
    eta: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    service_level: Optional[str] = None
    weight_kg: Optional[float] = None
    attributes: dict = Field(default_factory=dict)


class LogisticsContext(BaseModel):
    """Agent-ready shipment context.

    >>> s = Shipment(tracking_id="T1", status="created")
    >>> e = ShipmentEvent(code="PU", occurred_at=datetime(2024, 1, 1))
    >>> LogisticsContext(shipment=s, events=[e]).events[0].code
    'PU'
    """

    shipment: Shipment
    events: list[ShipmentEvent] = Field(default_factory=list)
