#!/usr/bin/env python3
"""Validate canonical retail and connector event schema contracts."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

from pydantic import ValidationError

from holiday_peak_lib.events import (
    CURRENT_EVENT_SCHEMA_VERSION,
    RETAIL_EVENT_TOPICS,
    SchemaCompatibilityPolicy,
    build_connector_event_payload,
    build_retail_event_payload,
    parse_connector_event,
    parse_retail_event,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "lib" / "tests" / "fixtures" / "event_schema_contracts"

EXPECTED_RETAIL_TOPICS = (
    "order-events",
    "payment-events",
    "return-events",
    "inventory-events",
    "shipment-events",
    "product-events",
    "user-events",
)

# No GoF pattern applies here; this is a direct fixture-driven contract gate.


def _load_fixture(name: str) -> dict[str, object]:
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"Contract fixture {name} must contain a JSON object")
    return payload


def _require_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise AssertionError(f"Contract fixture key '{key}' must be a string")
    return value


def _require_object(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise AssertionError(f"Contract fixture key '{key}' must be an object")
    return dict(value)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _validate_policy() -> None:
    policy = SchemaCompatibilityPolicy(CURRENT_EVENT_SCHEMA_VERSION)

    _assert(
        tuple(RETAIL_EVENT_TOPICS) == EXPECTED_RETAIL_TOPICS,
        "Retail event topic registry drifted from the governed canonical boundary",
    )
    _assert(
        policy.normalize(None) == CURRENT_EVENT_SCHEMA_VERSION,
        "Missing schema_version must default to 1.0",
    )
    _assert(
        policy.is_compatible("1.7"),
        "Same-major schema versions must remain compatible",
    )
    _assert(
        not policy.is_compatible("2.0"),
        "Breaking major versions must be rejected until a consumer major is added",
    )


def _validate_retail_contracts() -> None:
    legacy_order = parse_retail_event(
        _load_fixture("retail-order-created-envelope-legacy.json"),
        topic="order-events",
    )
    _assert(
        legacy_order.schema_version == CURRENT_EVENT_SCHEMA_VERSION,
        "Legacy retail payloads must parse as schema_version 1.0",
    )

    governed_fixture = _load_fixture("retail-user-updated-envelope-v1.0.json")
    governed_user = build_retail_event_payload(
        topic="user-events",
        event_type=_require_string(governed_fixture, "event_type"),
        data=_require_object(governed_fixture, "data"),
        schema_version=_require_string(governed_fixture, "schema_version"),
    )
    _assert(
        governed_user == governed_fixture,
        "Retail governed fixture drifted from canonical builder output",
    )

    additive_fixture = deepcopy(governed_fixture)
    additive_data = _require_object(additive_fixture, "data")
    additive_fixture["schema_version"] = "1.1"
    additive_data["new_marketing_flag"] = True
    additive_fixture["data"] = additive_data
    additive_payload = parse_retail_event(
        additive_fixture,
        topic="user-events",
    ).model_dump(mode="json")
    _assert(
        additive_payload["data"]["new_marketing_flag"] is True,
        "Retail consumers must tolerate additive same-major fields",
    )

    breaking_fixture = deepcopy(governed_fixture)
    breaking_fixture["schema_version"] = "2.0"
    try:
        parse_retail_event(breaking_fixture, topic="user-events")
    except (ValidationError, ValueError):
        pass
    else:
        raise AssertionError("Retail consumers must reject unsupported major versions")


def _validate_connector_contracts() -> None:
    legacy_connector = parse_connector_event(
        _load_fixture("connector-product-changed-envelope-legacy.json")
    )
    _assert(
        legacy_connector.schema_version == CURRENT_EVENT_SCHEMA_VERSION,
        "Legacy connector payloads must parse as schema_version 1.0",
    )

    governed_fixture = _load_fixture("connector-product-changed-envelope-v1.0.json")
    governed_connector = build_connector_event_payload(
        governed_fixture
    )
    _assert(
        governed_connector == governed_fixture,
        "Connector governed fixture drifted from canonical builder output",
    )

    additive_fixture = deepcopy(governed_fixture)
    additive_fixture["schema_version"] = "1.3"
    additive_fixture["upstream_revision"] = "rev-42"
    additive_connector = build_connector_event_payload(
        additive_fixture
    )
    _assert(
        additive_connector["upstream_revision"] == "rev-42",
        "Connector consumers must tolerate additive same-major fields",
    )

    breaking_fixture = deepcopy(governed_fixture)
    breaking_fixture["schema_version"] = "2.0"
    try:
        parse_connector_event(breaking_fixture)
    except (ValidationError, ValueError):
        pass
    else:
        raise AssertionError("Connector consumers must reject unsupported major versions")


def main() -> int:
    try:
        _validate_policy()
        _validate_retail_contracts()
        _validate_connector_contracts()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Event schema contract check failed: {exc}")
        return 1

    print("Event schema contract check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
