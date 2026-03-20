"""Holiday Peak Hub core micro-framework."""

from holiday_peak_lib.app_factory import build_service_app, create_standard_app
from holiday_peak_lib.utils.logging import configure_logging

# Initialize logging with Azure Monitor if connection string env vars are present.
configure_logging()

__all__ = [
    "build_service_app",
    "create_standard_app",
    "adapters",
    "agents",
    "events",
    "integrations",
    "mcp",
    "schemas",
    "utils",
    "config",
]
