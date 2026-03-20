"""Pydantic schemas for agents and adapters."""

from .acp import AcpPartnerProfile, AcpProduct
from .canonical import CategorySchema as CanonicalCategorySchema
from .canonical import FieldDef as CanonicalFieldDef
from .core import Product, RecommendationRequest, RecommendationResponse, UserContext
from .crm import CRMAccount, CRMContact, CRMContext, CRMInteraction
from .funnel import FunnelContext, FunnelMetric
from .inventory import InventoryContext, InventoryItem, WarehouseStock
from .logistics import LogisticsContext, Shipment, ShipmentEvent
from .pricing import PriceContext, PriceEntry
from .product import CanonicalProduct, CatalogProduct, ProductContext
from .search import (
    IntentClassification,
    SearchEnrichedProduct,
)
from .truth import (
    AssetMetadata,
    AttributeSource,
    AttributeStatus,
    AuditAction,
    AuditEvent,
    CategorySchema,
    EntityType,
    ExportJob,
    ExportResult,
    GapReport,
    GapReportTarget,
)
from .truth import IntentClassification as LegacyIntentClassification
from .truth import (
    ProductEnrichmentProposal,
    ProductStyle,
    ProductVariant,
    ProposedAttribute,
    Provenance,
)
from .truth import SearchEnrichedProduct as LegacySearchEnrichedProduct
from .truth import (
    SharePolicy,
    SourceType,
    TruthAttribute,
)
from .ucp import UcpCompliance, UcpImage, UcpMetadata, UcpPricing, UcpProduct

__all__ = [
    "AcpPartnerProfile",
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
    "CanonicalProduct",
    "ProductContext",
    "InventoryItem",
    "WarehouseStock",
    "InventoryContext",
    "PriceEntry",
    "PriceContext",
    "CanonicalFieldDef",
    "CanonicalCategorySchema",
    "UcpImage",
    "UcpPricing",
    "UcpCompliance",
    "UcpMetadata",
    "UcpProduct",
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
    "ExportJob",
    "ExportResult",
    "GapReport",
    "GapReportTarget",
    "ProductStyle",
    "ProductVariant",
    "ProductEnrichmentProposal",
    "ProposedAttribute",
    "Provenance",
    "SearchEnrichedProduct",
    "LegacySearchEnrichedProduct",
    "SharePolicy",
    "SourceType",
    "TruthAttribute",
    "IntentClassification",
    "LegacyIntentClassification",
]
