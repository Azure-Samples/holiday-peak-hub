"""Mapping helpers: SAP S/4HANA OData responses → canonical domain models.

Each function accepts a single OData entity dict and returns the
corresponding Pydantic model instance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from holiday_peak_lib.integrations.contracts import InventoryData, ProductData


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string or OData /Date(ms)/ to a datetime."""
    if not value:
        return None
    if value.startswith("/Date("):
        # OData v2 legacy format: /Date(1609459200000)/
        ms = int(value[6:].split(")")[0].split("+")[0].split("-")[0])
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def map_material_stock_to_inventory(record: dict[str, Any]) -> InventoryData:
    """Map an A_MatlStkInAcctMod OData entity to :class:`InventoryData`.

    SAP field reference
    -------------------
    Material           → sku
    Plant              → location_id
    StorageLocation    → appended to location_name
    MatlStkInAcctMod   → available_qty (unrestricted-use stock)
    """
    sku = record.get("Material") or record.get("Product") or ""
    location_id = record.get("Plant") or ""
    storage_loc = record.get("StorageLocation") or ""
    location_name = f"{location_id}/{storage_loc}".strip("/") or None

    available_qty = int(float(record.get("MatlStkInAcctMod") or 0))
    reserved_qty = int(float(record.get("QtyInTransit") or 0))
    on_order_qty = int(float(record.get("QtyInQualityInspection") or 0))
    reorder_point = record.get("ReorderThresholdQuantity")
    reorder_point = int(float(reorder_point)) if reorder_point is not None else None

    return InventoryData(
        sku=sku,
        location_id=location_id,
        location_name=location_name,
        available_qty=available_qty,
        reserved_qty=reserved_qty,
        on_order_qty=on_order_qty,
        reorder_point=reorder_point,
        last_updated=_parse_datetime(record.get("LastChangeDateTime")),
    )


def map_warehouse_bin_stock_to_inventory(record: dict[str, Any]) -> InventoryData:
    """Map an A_WarehouseStorageBinStock OData entity to :class:`InventoryData`.

    SAP field reference
    -------------------
    Product            → sku
    Warehouse          → location_id
    StorageBin         → appended to location_name
    StockQty           → available_qty
    """
    sku = record.get("Product") or record.get("Material") or ""
    warehouse = record.get("Warehouse") or ""
    bin_id = record.get("StorageBin") or ""
    location_name = f"{warehouse}/{bin_id}".strip("/") or None

    reorder_raw = record.get("ReorderThresholdQuantity")
    reorder_point = int(float(reorder_raw)) if reorder_raw is not None else None

    return InventoryData(
        sku=sku,
        location_id=warehouse,
        location_name=location_name,
        available_qty=int(float(record.get("StockQty") or 0)),
        reserved_qty=int(float(record.get("ReservedQty") or 0)),
        reorder_point=reorder_point,
        last_updated=_parse_datetime(record.get("LastChangeDate")),
    )


def map_product_to_product_data(record: dict[str, Any]) -> ProductData:
    """Map an A_Product OData entity to :class:`ProductData`.

    SAP field reference
    -------------------
    Product            → sku
    ProductDescription → title (first language entry if list)
    Brand              → brand
    ProductGroup       → category_path[0]
    """
    sku = record.get("Product") or record.get("Material") or ""

    # ProductDescription may be an inline list of {Language, ProductDescription}
    raw_desc = record.get("to_Description") or record.get("ProductDescription") or []
    if isinstance(raw_desc, list):
        title = next(
            (d.get("ProductDescription", "") for d in raw_desc if d.get("Language") == "EN"),
            raw_desc[0].get("ProductDescription", sku) if raw_desc else sku,
        )
    else:
        title = str(raw_desc) or sku

    category = record.get("ProductGroup") or record.get("Division") or ""

    return ProductData(
        sku=sku,
        title=title,
        brand=record.get("Brand") or None,
        category_path=[category] if category else [],
        status="active" if record.get("CrossPlantStatus") != "02" else "inactive",
        source_system="sap_s4hana",
        last_modified=_parse_datetime(record.get("LastChangeDate")),
        attributes={
            k: v
            for k, v in record.items()
            if k
            not in {
                "Product",
                "Material",
                "ProductDescription",
                "to_Description",
                "Brand",
                "ProductGroup",
                "Division",
                "CrossPlantStatus",
                "LastChangeDate",
            }
        },
    )
