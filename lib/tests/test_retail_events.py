"""Tests for canonical retail event schemas."""

import pytest
from holiday_peak_lib.events import build_retail_event_payload, parse_retail_event


def test_parse_order_event_with_legacy_id_alias() -> None:
    payload = {
        "event_type": "OrderCreated",
        "data": {
            "id": "order-123",
            "user_id": "user-1",
            "items": [],
            "total": 10.5,
            "status": "pending",
            "created_at": "2026-03-21T00:00:00Z",
        },
    }

    parsed = parse_retail_event(payload, topic="order-events")

    assert parsed.data.order_id == "order-123"
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
