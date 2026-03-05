"""Test fixtures for the Truth HITL service."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from truth_hitl.review_manager import ReviewItem


@pytest.fixture
def sample_review_item() -> ReviewItem:
    return ReviewItem(
        entity_id="prod-001",
        attr_id="attr-001",
        field_name="color",
        proposed_value="Midnight Blue",
        confidence=0.85,
        current_value=None,
        source="ai",
        proposed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        product_title="Winter Jacket",
        category_label="Apparel",
    )


@pytest.fixture
def another_review_item() -> ReviewItem:
    return ReviewItem(
        entity_id="prod-001",
        attr_id="attr-002",
        field_name="material",
        proposed_value="Polyester",
        confidence=0.72,
        current_value=None,
        source="ai",
        proposed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        product_title="Winter Jacket",
        category_label="Apparel",
    )
