"""Compatibility layer for connector protocols.

Canonical connector contracts now live in:
`holiday_peak_lib.connectors.protocols`
"""

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
]
