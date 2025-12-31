"""Logistics ETA computation service."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "logistics-eta-computation"
app = build_service_app(SERVICE_NAME)
