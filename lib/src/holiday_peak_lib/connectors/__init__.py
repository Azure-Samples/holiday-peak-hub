"""Connector contracts and registry exports."""

from holiday_peak_lib.connectors.protocols import (
    AnalyticsConnectorProtocol,
    AssetData,
    CRMConnectorProtocol,
    CommerceConnectorProtocol,
    CustomerData,
    DAMConnectorProtocol,
    IdentityConnectorProtocol,
    IntegrationConnectorProtocol,
    InventoryConnectorProtocol,
    InventoryData,
    OrderData,
    PIMConnectorProtocol,
    ProductData,
    SegmentData,
    WorkforceConnectorProtocol,
)
from holiday_peak_lib.connectors.registry import ConnectorRegistration, ConnectorRegistry

__all__ = [
    "AssetData",
    "ProductData",
    "InventoryData",
    "CustomerData",
    "OrderData",
    "SegmentData",
    "PIMConnectorProtocol",
    "DAMConnectorProtocol",
    "InventoryConnectorProtocol",
    "CRMConnectorProtocol",
    "CommerceConnectorProtocol",
    "AnalyticsConnectorProtocol",
    "IntegrationConnectorProtocol",
    "IdentityConnectorProtocol",
    "WorkforceConnectorProtocol",
    "ConnectorRegistration",
    "ConnectorRegistry",
]
