"""Adapter package exports."""

from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter, BaseConnector
from holiday_peak_lib.adapters.mock_adapters import (
	MockCRMAdapter,
	MockFunnelAdapter,
	MockInventoryAdapter,
	MockLogisticsAdapter,
	MockPricingAdapter,
	MockProductAdapter,
)

__all__ = [
	"AdapterError",
	"BaseAdapter",
	"BaseConnector",
	"MockCRMAdapter",
	"MockFunnelAdapter",
	"MockInventoryAdapter",
	"MockLogisticsAdapter",
	"MockPricingAdapter",
	"MockProductAdapter",
]
