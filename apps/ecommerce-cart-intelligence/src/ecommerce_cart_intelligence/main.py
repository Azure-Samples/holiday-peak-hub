"""Ecommerce Cart Intelligence service entrypoint."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "ecommerce-cart-intelligence"
app = build_service_app(SERVICE_NAME)
