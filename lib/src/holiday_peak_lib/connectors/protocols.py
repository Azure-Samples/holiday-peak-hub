"""Protocol interfaces and domain models for enterprise connectors.

These protocols define contracts for vendor-specific connectors. Connector
implementations should extend `BaseAdapter` and satisfy one or more protocols.

Constraint:
- Product enrichment must use company-owned source data only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field


class AssetData(BaseModel):
    id: str
    url: str
    content_type: str
    filename: str | None = None
    size_bytes: int | None = None
    width: int | None = None
    height: int | None = None
    alt_text: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ProductData(BaseModel):
    sku: str
    title: str
    description: str | None = None
    short_description: str | None = None
    brand: str | None = None
    category_path: list[str] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list)
    variants: list[str] = Field(default_factory=list)
    status: str = "active"
    source_system: str | None = None
    last_modified: datetime | None = None


class InventoryData(BaseModel):
    sku: str
    location_id: str
    location_name: str | None = None
    available_qty: int
    reserved_qty: int = 0
    on_order_qty: int = 0
    reorder_point: int | None = None
    last_updated: datetime | None = None


class CustomerData(BaseModel):
    customer_id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    segments: list[str] = Field(default_factory=list)
    loyalty_tier: str | None = None
    lifetime_value: float | None = None
    preferences: dict = Field(default_factory=dict)
    consent: dict = Field(default_factory=dict)
    last_activity: datetime | None = None


class OrderData(BaseModel):
    order_id: str
    customer_id: str | None = None
    status: str
    total: float
    currency: str = "USD"
    items: list[dict] = Field(default_factory=list)
    shipping_address: dict | None = None
    billing_address: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SegmentData(BaseModel):
    segment_id: str
    name: str
    description: str | None = None
    criteria: dict = Field(default_factory=dict)
    member_count: int | None = None


class PIMConnectorProtocol(ABC):
    @abstractmethod
    async def get_product(self, sku: str) -> ProductData | None:
        """Fetch a single product by SKU."""

    @abstractmethod
    async def list_products(
        self,
        *,
        category: str | None = None,
        modified_since: datetime | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[ProductData]:
        """List products with optional filters."""

    @abstractmethod
    async def search_products(self, query: str, limit: int = 50) -> list[ProductData]:
        """Search products by keyword."""

    @abstractmethod
    async def get_product_assets(self, sku: str) -> list[AssetData]:
        """Get assets linked to a product."""

    @abstractmethod
    async def get_categories(self) -> list[dict]:
        """Get category taxonomy."""


class DAMConnectorProtocol(ABC):
    @abstractmethod
    async def get_asset(self, asset_id: str) -> AssetData | None:
        """Fetch asset by id."""

    @abstractmethod
    async def get_assets_by_product(self, sku: str) -> list[AssetData]:
        """Get assets by SKU."""

    @abstractmethod
    async def search_assets(
        self,
        query: str,
        *,
        tags: list[str] | None = None,
        content_type: str | None = None,
        limit: int = 50,
    ) -> list[AssetData]:
        """Search assets by query and filters."""

    @abstractmethod
    async def get_transformed_url(
        self,
        asset_id: str,
        *,
        width: int | None = None,
        height: int | None = None,
        output_format: str | None = None,
        quality: int | None = None,
    ) -> str:
        """Get transformed asset URL."""


class InventoryConnectorProtocol(ABC):
    @abstractmethod
    async def get_inventory(self, sku: str, location_id: str | None = None) -> list[InventoryData]:
        """Get inventory levels for SKU."""

    @abstractmethod
    async def get_available_to_promise(self, sku: str, quantity: int) -> list[dict]:
        """Get ATP locations for requested quantity."""

    @abstractmethod
    async def reserve_inventory(
        self,
        sku: str,
        location_id: str,
        quantity: int,
        reference_id: str,
    ) -> dict:
        """Create soft reservation."""

    @abstractmethod
    async def release_reservation(self, reservation_id: str) -> bool:
        """Release a reservation."""

    @abstractmethod
    async def get_replenishment_recommendations(
        self,
        location_id: str | None = None,
    ) -> list[dict]:
        """Get replenishment recommendations."""


class CRMConnectorProtocol(ABC):
    @abstractmethod
    async def get_customer(self, customer_id: str) -> CustomerData | None:
        """Fetch a customer profile."""

    @abstractmethod
    async def get_customer_by_email(self, email: str) -> CustomerData | None:
        """Find customer by email."""

    @abstractmethod
    async def get_customer_segments(self, customer_id: str) -> list[SegmentData]:
        """List segments for customer."""

    @abstractmethod
    async def get_purchase_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderData]:
        """Get purchase history."""

    @abstractmethod
    async def update_customer(self, customer_id: str, updates: dict) -> CustomerData:
        """Update customer profile."""

    @abstractmethod
    async def track_event(self, customer_id: str, event_type: str, properties: dict) -> None:
        """Track customer event."""


class CommerceConnectorProtocol(ABC):
    @abstractmethod
    async def get_order(self, order_id: str) -> OrderData | None:
        """Fetch order by id."""

    @abstractmethod
    async def list_orders(
        self,
        *,
        customer_id: str | None = None,
        status: str | None = None,
        since: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[OrderData]:
        """List orders with optional filters."""

    @abstractmethod
    async def create_order(self, order_data: dict) -> OrderData:
        """Create order."""

    @abstractmethod
    async def update_order_status(self, order_id: str, status: str) -> OrderData:
        """Update order status."""

    @abstractmethod
    async def get_cart(self, cart_id: str) -> dict | None:
        """Get cart contents."""

    @abstractmethod
    async def sync_product(self, product: ProductData) -> dict:
        """Sync product to commerce platform."""


class AnalyticsConnectorProtocol(ABC):
    @abstractmethod
    async def query(self, sql: str, params: dict | None = None) -> list[dict]:
        """Execute query."""

    @abstractmethod
    async def get_product_performance(
        self,
        sku: str,
        *,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Get product performance metrics."""

    @abstractmethod
    async def get_customer_predictions(self, customer_id: str) -> dict:
        """Get customer prediction payload."""

    @abstractmethod
    async def get_demand_forecast(
        self,
        sku: str,
        location_id: str | None = None,
        horizon_days: int = 30,
    ) -> list[dict]:
        """Get demand forecast."""


class IntegrationConnectorProtocol(ABC):
    @abstractmethod
    async def publish_event(self, topic: str, payload: dict) -> dict:
        """Publish integration event."""

    @abstractmethod
    async def consume_events(self, topic: str, limit: int = 100) -> list[dict]:
        """Consume integration events."""


class IdentityConnectorProtocol(ABC):
    @abstractmethod
    async def get_user(self, user_id: str) -> dict | None:
        """Fetch user identity."""

    @abstractmethod
    async def get_consent(self, subject_id: str) -> dict | None:
        """Fetch consent/preferences."""


class WorkforceConnectorProtocol(ABC):
    @abstractmethod
    async def get_schedule(self, location_id: str, date: datetime) -> list[dict]:
        """Get schedule for location/date."""

    @abstractmethod
    async def assign_task(self, employee_id: str, task_type: str, details: dict) -> dict:
        """Assign task to employee."""

    @abstractmethod
    async def get_task_status(self, task_id: str) -> dict:
        """Get task status."""
