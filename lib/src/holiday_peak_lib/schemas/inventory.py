"""Canonical inventory schemas.

Captures inventory state for agent use in availability, fulfillment, and
replenishment scenarios covered in the business summary. Doctests highlight
basic construction and defaults.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WarehouseStock(BaseModel):
    """Stock snapshot for a specific warehouse.

    >>> WarehouseStock(warehouse_id="W1", available=5).reserved
    0
    """

    warehouse_id: str
    available: int
    reserved: int = 0
    location: Optional[str] = None
    updated_at: Optional[datetime] = None


class InventoryItem(BaseModel):
    """Standardized inventory item view.

    >>> InventoryItem(sku="SKU-1", available=10).available
    10
    >>> InventoryItem(sku="SKU-1", available=0, status="backorder").status
    'backorder'
    """

    sku: str
    available: int
    reserved: int = 0
    backorder_date: Optional[datetime] = None
    safety_stock: Optional[int] = None
    lead_time_days: Optional[int] = None
    status: Optional[str] = None
    attributes: dict = Field(default_factory=dict)


class InventoryContext(BaseModel):
    """Aggregate inventory context for agents.

    >>> item = InventoryItem(sku="SKU-1", available=2)
    >>> wh = WarehouseStock(warehouse_id="W1", available=2)
    >>> InventoryContext(item=item, warehouses=[wh]).warehouses[0].warehouse_id
    'W1'
    """

    item: InventoryItem
    warehouses: list[WarehouseStock] = Field(default_factory=list)
