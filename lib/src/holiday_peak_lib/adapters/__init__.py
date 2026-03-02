"""Adapter package exports."""

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter, BaseConnector
from holiday_peak_lib.adapters.crud_adapter import BaseCRUDAdapter
from holiday_peak_lib.adapters.external_api_adapter import BaseExternalAPIAdapter
from holiday_peak_lib.adapters.mcp_adapter import BaseMCPAdapter
from holiday_peak_lib.adapters.mock_adapters import (
    MockCRMAdapter,
    MockFunnelAdapter,
    MockInventoryAdapter,
    MockLogisticsAdapter,
    MockPricingAdapter,
    MockProductAdapter,
)

__all__ = [
    "AcpCatalogMapper",
    "AdapterError",
    "BaseAdapter",
    "BaseConnector",
    "BaseMCPAdapter",
    "BaseCRUDAdapter",
    "BaseExternalAPIAdapter",
    "MockCRMAdapter",
    "MockFunnelAdapter",
    "MockInventoryAdapter",
    "MockLogisticsAdapter",
    "MockPricingAdapter",
    "MockProductAdapter",
]
