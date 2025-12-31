"""Product consistency validation service."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "product-management-consistency-validation"
app = build_service_app(SERVICE_NAME)
