"""Inventory JIT replenishment service."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "inventory-jit-replenishment"
app = build_service_app(SERVICE_NAME)
