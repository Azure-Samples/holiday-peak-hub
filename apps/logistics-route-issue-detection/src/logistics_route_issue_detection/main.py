"""Logistics route issue detection service."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "logistics-route-issue-detection"
app = build_service_app(SERVICE_NAME)
