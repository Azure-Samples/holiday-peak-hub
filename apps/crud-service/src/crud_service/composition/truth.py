"""Truth-layer route composition."""

from crud_service.routes import (
    audit_trail,
    completeness,
    proposed_attributes,
    schemas_registry,
    truth_attributes,
    ucp_products,
)
from fastapi import FastAPI


def include_truth_routes(app: FastAPI) -> None:
    """Register truth-layer API routes."""
    app.include_router(truth_attributes.router, prefix="/api", tags=["Truth Attributes"])
    app.include_router(proposed_attributes.router, prefix="/api", tags=["Proposed Attributes"])
    app.include_router(schemas_registry.router, prefix="/api", tags=["Schemas Registry"])
    app.include_router(completeness.router, prefix="/api", tags=["Completeness"])
    app.include_router(audit_trail.router, prefix="/api", tags=["Audit Trail"])
    app.include_router(ucp_products.router, prefix="/api", tags=["UCP Products"])
