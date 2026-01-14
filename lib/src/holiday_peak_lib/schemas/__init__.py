"""Pydantic schemas for agents and adapters."""

from .core import UserContext, Product, RecommendationRequest, RecommendationResponse
from .crm import CRMAccount, CRMContact, CRMContext, CRMInteraction
from .product import CatalogProduct, ProductContext
from .inventory import InventoryItem, WarehouseStock, InventoryContext
from .pricing import PriceEntry, PriceContext
from .logistics import Shipment, ShipmentEvent, LogisticsContext
from .funnel import FunnelMetric, FunnelContext

__all__ = [
    "UserContext",
    "Product",
    "RecommendationRequest",
    "RecommendationResponse",
    "CRMAccount",
    "CRMContact",
    "CRMContext",
    "CRMInteraction",
    "CatalogProduct",
    "ProductContext",
    "InventoryItem",
    "WarehouseStock",
    "InventoryContext",
    "PriceEntry",
    "PriceContext",
    "Shipment",
    "ShipmentEvent",
    "LogisticsContext",
    "FunnelMetric",
    "FunnelContext",
]
