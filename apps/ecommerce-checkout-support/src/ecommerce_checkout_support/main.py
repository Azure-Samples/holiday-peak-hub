"""Ecommerce Checkout Support service entrypoint."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "ecommerce-checkout-support"
app = build_service_app(SERVICE_NAME)
