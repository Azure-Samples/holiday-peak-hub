"""Middleware wiring helpers for service apps."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from holiday_peak_lib.utils import (
    CORRELATION_HEADER,
    clear_correlation_id,
    set_correlation_id,
)


def register_correlation_middleware(app: FastAPI) -> None:
    """Register correlation middleware on the provided app."""

    @app.middleware("http")
    async def correlation_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming_correlation = (
            request.headers.get(CORRELATION_HEADER)
            or request.headers.get("X-Correlation-ID")
            or request.headers.get("x-request-id")
        )
        correlation_id = set_correlation_id(incoming_correlation)
        try:
            response = await call_next(request)
        finally:
            clear_correlation_id()
        response.headers["X-Correlation-ID"] = correlation_id
        return response
