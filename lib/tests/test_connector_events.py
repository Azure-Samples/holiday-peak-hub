"""Tests for connector synchronization event schemas."""

from holiday_peak_lib.events import parse_connector_event
from holiday_peak_lib.events.connector_events import InventoryUpdated, ProductChanged


def test_parse_product_changed_event() -> None:
    payload = {
        "event_type": "ProductChanged",
        "source_system": "akeneo",
        "entity_id": "sku-1",
        "product_id": "sku-1",
        "name": "Updated Name",
    }

    event = parse_connector_event(payload)

    assert isinstance(event, ProductChanged)
    assert event.product_id == "sku-1"
    assert event.source_system == "akeneo"


def test_parse_inventory_updated_event() -> None:
    payload = {
        "event_type": "InventoryUpdated",
        "source_system": "sap-s4",
        "entity_id": "sku-2",
        "product_id": "sku-2",
        "quantity": 12,
    }

    event = parse_connector_event(payload)

    assert isinstance(event, InventoryUpdated)
    assert event.quantity == 12
