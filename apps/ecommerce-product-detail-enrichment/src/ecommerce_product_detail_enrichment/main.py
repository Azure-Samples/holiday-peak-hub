"""Ecommerce Product Detail Enrichment service entrypoint."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "ecommerce-product-detail-enrichment"
app = build_service_app(SERVICE_NAME)
