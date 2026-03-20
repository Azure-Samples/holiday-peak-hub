"""Logging helpers with Azure Monitor + OpenTelemetry integration."""

import json
import logging
import os
import tracemalloc
from contextlib import contextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Awaitable, Callable, Optional

from holiday_peak_lib.utils.correlation import get_correlation_id

DEFAULT_APP_NAME = os.getenv("APP_NAME", "unknown-app")


class _CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or ""
        return True


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "app": getattr(record, "app_name", DEFAULT_APP_NAME),
            "correlation_id": getattr(record, "correlation_id", ""),
            "message": record.getMessage(),
        }
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, ensure_ascii=False)


def _ensure_tracemalloc() -> None:
    if not tracemalloc.is_tracing():
        tracemalloc.start()


def _token_estimate(payload: Any) -> int:
    text = "" if payload is None else str(payload)
    # Rough heuristic: ~4 chars per token
    return max(1, int(len(text) / 4))


def configure_logging(
    connection_string: Optional[str] = None, app_name: Optional[str] = None
) -> logging.Logger:
    resolved_app = app_name or DEFAULT_APP_NAME
    base_logger = logging.getLogger(f"holiday-peak-lib.{resolved_app}")
    if base_logger.handlers:
        return logging.LoggerAdapter(base_logger, {"app_name": resolved_app})

    base_logger.setLevel(logging.INFO)
    conn = (
        connection_string
        or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        or os.getenv("APPINSIGHTS_CONNECTION_STRING")
    )
    if conn:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(connection_string=conn)
            base_logger.info("Azure Monitor logging enabled via configure_azure_monitor.")
        except ImportError:
            base_logger.warning(
                "Azure Monitor logging disabled: missing or incompatible OpenTelemetry packages."
            )
        except Exception as exc:
            base_logger.warning("Azure Monitor logging setup error: %s", exc)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.addFilter(_CorrelationIdFilter())
    formatter = _JsonLogFormatter()
    stream_handler.setFormatter(formatter)
    base_logger.addHandler(stream_handler)
    base_logger.propagate = False
    _ensure_tracemalloc()
    return logging.LoggerAdapter(base_logger, {"app_name": resolved_app})


async def log_async_operation(
    logger: logging.Logger,
    name: str,
    intent: Optional[str],
    func: Callable[[], Awaitable[Any]],
    token_count: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> Any:
    _ensure_tracemalloc()
    start_mem, _ = tracemalloc.get_traced_memory()
    start = perf_counter()
    tokens = token_count if token_count is not None else _token_estimate(metadata)
    app_name = getattr(logger, "extra", {}).get("app_name", DEFAULT_APP_NAME)
    try:
        result = await func()
        duration_ms = (perf_counter() - start) * 1000
        end_mem, _ = tracemalloc.get_traced_memory()
        mem_delta = end_mem - start_mem
        status = "success" if result is not None else "empty"
        logger.info(
            "app=%s op=%s intent=%s status=%s duration_ms=%.2f mem_delta_bytes=%d token_estimate=%d metadata=%s",
            app_name,
            name,
            intent,
            status,
            duration_ms,
            mem_delta,
            tokens,
            metadata,
        )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        duration_ms = (perf_counter() - start) * 1000
        end_mem, _ = tracemalloc.get_traced_memory()
        mem_delta = end_mem - start_mem
        logger.exception(
            "app=%s op=%s intent=%s status=failure duration_ms=%.2f mem_delta_bytes=%d token_estimate=%d metadata=%s error=%s",
            app_name,
            name,
            intent,
            duration_ms,
            mem_delta,
            tokens,
            metadata,
            exc,
        )
        raise


@contextmanager
def log_operation(
    logger: logging.Logger,
    name: str,
    intent: Optional[str],
    token_count: Optional[int] = None,
    metadata: Optional[dict] = None,
):
    _ensure_tracemalloc()
    start_mem, _ = tracemalloc.get_traced_memory()
    start = perf_counter()
    tokens = token_count if token_count is not None else _token_estimate(metadata)
    app_name = getattr(logger, "extra", {}).get("app_name", DEFAULT_APP_NAME)
    try:
        yield
        duration_ms = (perf_counter() - start) * 1000
        end_mem, _ = tracemalloc.get_traced_memory()
        mem_delta = end_mem - start_mem
        logger.info(
            "app=%s op=%s intent=%s status=success duration_ms=%.2f mem_delta_bytes=%d token_estimate=%d metadata=%s",
            app_name,
            name,
            intent,
            duration_ms,
            mem_delta,
            tokens,
            metadata,
        )
    except Exception as exc:  # pylint: disable=broad-except
        duration_ms = (perf_counter() - start) * 1000
        end_mem, _ = tracemalloc.get_traced_memory()
        mem_delta = end_mem - start_mem
        logger.exception(
            "app=%s op=%s intent=%s status=failure duration_ms=%.2f mem_delta_bytes=%d token_estimate=%d metadata=%s error=%s",
            app_name,
            name,
            intent,
            duration_ms,
            mem_delta,
            tokens,
            metadata,
            exc,
        )
        raise
