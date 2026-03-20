"""Adapter package exports."""

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter, BaseConnector
from holiday_peak_lib.adapters.crud_adapter import BaseCRUDAdapter
from holiday_peak_lib.adapters.dam_image_analysis import DAMImageAnalysisAdapter
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
from holiday_peak_lib.adapters.protocol_mapper import ProtocolMapper
from holiday_peak_lib.adapters.ucp_mapper import UcpProtocolMapper

__all__ = [
    "AcpCatalogMapper",
    "AdapterError",
    "BaseAdapter",
    "BaseConnector",
    "BaseMCPAdapter",
    "BaseCRUDAdapter",
    "DAMImageAnalysisAdapter",
    "BaseExternalAPIAdapter",
    "MockCRMAdapter",
    "MockFunnelAdapter",
    "MockInventoryAdapter",
    "MockLogisticsAdapter",
    "MockPricingAdapter",
    "MockProductAdapter",
    "ProtocolMapper",
    "UcpProtocolMapper",
]
