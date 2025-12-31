"""Inventory alerts and triggers service."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "inventory-alerts-triggers"
app = build_service_app(SERVICE_NAME)
