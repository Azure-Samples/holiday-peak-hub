"""CRUD service route composition groups."""

from crud_service.composition.commerce import include_commerce_routes
from crud_service.composition.platform import include_platform_routes
from crud_service.composition.staff import include_staff_routes
from crud_service.composition.truth import include_truth_routes
from fastapi import FastAPI


def register_routes(app: FastAPI) -> None:
    """Register all CRUD route groups on the FastAPI app."""
    include_platform_routes(app)
    include_commerce_routes(app)
    include_staff_routes(app)
    include_truth_routes(app)


__all__ = ["register_routes"]
