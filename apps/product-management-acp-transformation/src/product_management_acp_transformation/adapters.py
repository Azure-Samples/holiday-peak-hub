"""Adapters for the product ACP transformation service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter
from holiday_peak_lib.adapters.product_adapter import ProductConnector


@dataclass
class AcpTransformationAdapters:
    """Container for ACP transformation adapters."""

    products: ProductConnector
    mapper: AcpCatalogMapper


def build_acp_transformation_adapters(
    *, product_connector: Optional[ProductConnector] = None
) -> AcpTransformationAdapters:
    """Create adapters for ACP transformation workflows."""
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    mapper = AcpCatalogMapper()
    return AcpTransformationAdapters(products=products, mapper=mapper)
