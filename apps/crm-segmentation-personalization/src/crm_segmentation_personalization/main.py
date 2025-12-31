"""CRM segmentation and personalization service."""
from holiday_peak_lib.app_factory import build_service_app

SERVICE_NAME = "crm-segmentation-personalization"
app = build_service_app(SERVICE_NAME)
