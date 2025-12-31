"""Inventory health check service."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "inventory-health-check"
app = build_service_app(SERVICE_NAME)
