"""Connector contracts, registry, and writeback exports."""

from holiday_peak_lib.integrations.dam_generic import DAMConnectionConfig, GenericDAMConnector
from holiday_peak_lib.integrations.pim_writeback import (
    CircuitBreaker,
    CircuitBreakerState,
    PIMWritebackManager,
    ProductWritebackResult,
    TenantConfig,
    WritebackResult,
    WritebackStatus,
)
from holiday_peak_lib.integrations.contracts import (
    AnalyticsConnectorBase,
    AssetData,
    CommerceConnectorBase,
    CRMConnectorBase,
    CustomerData,
    DAMConnectorBase,
    IdentityConnectorBase,
    IntegrationConnectorBase,
    InventoryConnectorBase,
    InventoryData,
    OrderData,
    PIMConnectorBase,
    ProductData,
    SegmentData,
    WorkforceConnectorBase,
)
from holiday_peak_lib.integrations.registry import ConnectorRegistration, ConnectorRegistry

__all__ = [
    "AssetData",
    "ProductData",
    "InventoryData",
    "CustomerData",
    "OrderData",
    "SegmentData",
    "PIMConnectorBase",
    "DAMConnectorBase",
    "InventoryConnectorBase",
    "CRMConnectorBase",
    "CommerceConnectorBase",
    "AnalyticsConnectorBase",
    "IntegrationConnectorBase",
    "IdentityConnectorBase",
    "WorkforceConnectorBase",
    "ConnectorRegistration",
    "ConnectorRegistry",
    "DAMConnectionConfig",
    "GenericDAMConnector",
    "CircuitBreaker",
    "CircuitBreakerState",
    "PIMWritebackManager",
    "ProductWritebackResult",
    "TenantConfig",
    "WritebackResult",
    "WritebackStatus",
]
