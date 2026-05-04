"""Holiday Peak Hub core micro-framework."""

# --- Early SDK compatibility patch -------------------------------------------
# azure-ai-projects <=2.1.0 telemetry instrumentor reads
# span.span_instance.attributes, but OpenTelemetry NonRecordingSpan lacks that
# attribute.  Patch the class *before* any SDK instrumentation runs.
from opentelemetry.trace import NonRecordingSpan as _NRS  # noqa: E402

if not hasattr(_NRS, "attributes"):
    _NRS.attributes = None  # type: ignore[attr-defined]

# Ensure a real TracerProvider is configured so NonRecordingSpan is never
# produced at runtime.  If Azure Monitor is configured later it will override.
from opentelemetry import trace as _trace  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider as _TracerProvider  # noqa: E402

if not isinstance(_trace.get_tracer_provider(), _TracerProvider):
    try:
        _trace.set_tracer_provider(_TracerProvider())
    # pylint: disable-next=broad-exception-caught
    except Exception:  # pragma: no cover - already set by another init path
        pass
# -----------------------------------------------------------------------------

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
    "messaging",
    "schemas",
    "self_healing",
    "utils",
    "config",
]
