"""Pydantic schemas for agents and adapters."""

from .acp import AcpProduct
from .core import Product, RecommendationRequest, RecommendationResponse, UserContext
from .crm import CRMAccount, CRMContact, CRMContext, CRMInteraction
from .funnel import FunnelContext, FunnelMetric
from .inventory import InventoryContext, InventoryItem, WarehouseStock
from .logistics import LogisticsContext, Shipment, ShipmentEvent
from .pricing import PriceContext, PriceEntry
from .product import CatalogProduct, ProductContext
from .truth import (
    AssetMetadata,
    AttributeSource,
    AttributeStatus,
    AuditAction,
    AuditEvent,
    CategorySchema,
    EntityType,
    GapReport,
    GapReportTarget,
    ProductStyle,
    ProductVariant,
    ProposedAttribute,
    Provenance,
    SharePolicy,
    TruthAttribute,
)

__all__ = [
    "AcpProduct",
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
    # Truth Layer models
    "AssetMetadata",
    "AuditAction",
    "AuditEvent",
    "AttributeSource",
    "AttributeStatus",
    "CategorySchema",
    "EntityType",
    "GapReport",
    "GapReportTarget",
    "ProductStyle",
    "ProductVariant",
    "ProposedAttribute",
    "Provenance",
    "SharePolicy",
    "TruthAttribute",
]
