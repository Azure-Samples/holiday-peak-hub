"""Tests for canonical retail event schemas."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from holiday_peak_lib.events import (
    CURRENT_EVENT_SCHEMA_VERSION,
    SchemaCompatibilityPolicy,
    build_retail_event_payload,
    parse_retail_event,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "event_schema_contracts"


def _load_contract_fixture(name: str) -> dict[str, object]:
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_parse_order_event_with_legacy_id_alias() -> None:
    payload = _load_contract_fixture("retail-order-created-envelope-legacy.json")

    parsed = parse_retail_event(payload, topic="order-events")

    assert parsed.data.order_id == "order-legacy"
    assert parsed.schema_version == CURRENT_EVENT_SCHEMA_VERSION
    assert parsed.timestamp == "2026-03-21T00:00:00Z"


def test_build_retail_event_payload_rejects_invalid_return_event() -> None:
    with pytest.raises(ValueError, match="return_id"):
        build_retail_event_payload(
            topic="return-events",
            event_type="ReturnRequested",
            data={
                "order_id": "order-1",
                "status": "requested",
            },
        )


def test_build_product_event_payload_normalizes_product_id_alias() -> None:
    payload = build_retail_event_payload(
        topic="product-events",
        event_type="ProductUpdated",
        data={
            "id": "sku-11",
            "name": "Widget",
            "category_id": "cat-1",
            "price": 18.0,
        },
    )

    assert payload["schema_version"] == CURRENT_EVENT_SCHEMA_VERSION
    assert payload["event_type"] == "ProductUpdated"
    assert payload["data"]["product_id"] == "sku-11"
    assert payload["data"]["sku"] == "sku-11"


def test_build_user_event_payload_writes_explicit_schema_version() -> None:
    fixture = _load_contract_fixture("retail-user-updated-envelope-v1.0.json")

    payload = build_retail_event_payload(
        topic="user-events",
        event_type=str(fixture["event_type"]),
        data=dict(fixture["data"]),
        schema_version=str(fixture["schema_version"]),
    )

    assert payload == fixture


def test_parse_retail_event_accepts_same_major_additive_fields() -> None:
    payload = deepcopy(_load_contract_fixture("retail-user-updated-envelope-v1.0.json"))
    payload["schema_version"] = "1.1"
    payload["data"] = dict(payload["data"])
    payload["data"]["loyalty_tier"] = "gold"

    parsed = parse_retail_event(payload, topic="user-events")

    assert parsed.schema_version == "1.1"
    assert parsed.model_dump(mode="json")["data"]["loyalty_tier"] == "gold"


def test_parse_retail_event_rejects_unknown_major_schema_version() -> None:
    payload = deepcopy(_load_contract_fixture("retail-user-updated-envelope-v1.0.json"))
    payload["schema_version"] = "2.0"

    with pytest.raises(ValueError, match="Unsupported schema_version major"):
        parse_retail_event(payload, topic="user-events")


def test_schema_policy_treats_same_major_versions_as_compatible() -> None:
    policy = SchemaCompatibilityPolicy(CURRENT_EVENT_SCHEMA_VERSION)

    assert policy.is_compatible("1.9") is True
    assert policy.is_compatible("2.0") is False
