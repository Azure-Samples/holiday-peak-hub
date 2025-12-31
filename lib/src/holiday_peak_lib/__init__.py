"""Holiday Peak Hub core micro-framework."""
from holiday_peak_lib.utils.logging import configure_logging

# Initialize logging with Azure Monitor if connection string env vars are present.
configure_logging()

__all__ = [
    "adapters",
    "agents",
    "schemas",
    "utils",
    "config",
]
