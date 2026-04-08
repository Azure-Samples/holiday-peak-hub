"""Tests for connector synchronization event schemas."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from holiday_peak_lib.events import (
    CURRENT_EVENT_SCHEMA_VERSION,
    build_connector_event_payload,
    parse_connector_event,
)
from holiday_peak_lib.events.connector_events import InventoryUpdated, ProductChanged

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "event_schema_contracts"


def _load_contract_fixture(name: str) -> dict[str, object]:
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_parse_product_changed_event() -> None:
    payload = _load_contract_fixture("connector-product-changed-envelope-legacy.json")

    event = parse_connector_event(payload)

    assert isinstance(event, ProductChanged)
    assert event.product_id == "sku-legacy"
    assert event.schema_version == CURRENT_EVENT_SCHEMA_VERSION
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


def test_build_connector_event_payload_writes_explicit_schema_version() -> None:
    fixture = _load_contract_fixture("connector-product-changed-envelope-v1.0.json")

    payload = build_connector_event_payload(fixture)

    assert payload == fixture


def test_parse_connector_event_accepts_same_major_additive_fields() -> None:
    payload = deepcopy(_load_contract_fixture("connector-product-changed-envelope-v1.0.json"))
    payload["schema_version"] = "1.2"
    payload["upstream_revision"] = "r42"

    event = parse_connector_event(payload)

    assert event.schema_version == "1.2"
    assert event.model_dump(mode="json")["upstream_revision"] == "r42"


def test_parse_connector_event_rejects_unknown_major_schema_version() -> None:
    payload = deepcopy(_load_contract_fixture("connector-product-changed-envelope-v1.0.json"))
    payload["schema_version"] = "2.0"

    with pytest.raises(ValueError, match="Unsupported schema_version major"):
        parse_connector_event(payload)
