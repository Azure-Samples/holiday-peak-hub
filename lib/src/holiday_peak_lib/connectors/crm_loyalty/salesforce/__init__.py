"""Salesforce CRM & Marketing Cloud connector package."""

from .connector import SalesforceCRMConnector
from .auth import SalesforceAuth
from .mappings import map_contact_to_customer, map_order_to_order_data, map_campaign_to_segment

__all__ = [
    "SalesforceCRMConnector",
    "SalesforceAuth",
    "map_contact_to_customer",
    "map_order_to_order_data",
    "map_campaign_to_segment",
]
