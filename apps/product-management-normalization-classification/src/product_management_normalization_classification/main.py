"""Product normalization and classification service."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "product-management-normalization-classification"
app = build_service_app(SERVICE_NAME)
