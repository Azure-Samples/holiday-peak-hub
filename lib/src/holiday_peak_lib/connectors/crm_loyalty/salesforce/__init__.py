"""Salesforce CRM & Marketing Cloud connector package."""

from .auth import SalesforceAuth
from .connector import SalesforceCRMConnector
from .mappings import map_campaign_to_segment, map_contact_to_customer, map_order_to_order_data

__all__ = [
    "SalesforceCRMConnector",
    "SalesforceAuth",
    "map_contact_to_customer",
    "map_order_to_order_data",
    "map_campaign_to_segment",
]
