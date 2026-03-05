"""Unit tests for the ReviewManager."""

from __future__ import annotations

import pytest
from truth_hitl.review_manager import ReviewDecision, ReviewManager


@pytest.fixture
def manager(sample_review_item, another_review_item):
    m = ReviewManager()
    m.enqueue(sample_review_item)
    m.enqueue(another_review_item)
    return m


def test_list_pending_returns_all(manager):
    items = manager.list_pending()
    assert len(items) == 2


def test_list_pending_filter_by_entity(manager):
    items = manager.list_pending(entity_id="prod-001")
    assert all(i.entity_id == "prod-001" for i in items)
    assert len(items) == 2


def test_list_pending_filter_by_field(manager):
    items = manager.list_pending(field_name="color")
    assert len(items) == 1
    assert items[0].field_name == "color"


def test_get_by_entity(manager):
    items = manager.get_by_entity("prod-001")
    assert len(items) == 2


def test_stats_initial(manager):
    stats = manager.stats()
    assert stats["pending_review"] == 2
    assert stats.get("approved", 0) == 0
    assert stats.get("rejected", 0) == 0


def test_approve_all(manager):
    decision = ReviewDecision(reviewed_by="staff-1")
    approved = manager.approve("prod-001", decision)
    assert len(approved) == 2
    assert all(i.status == "approved" for i in approved)
    stats = manager.stats()
    assert stats["approved"] == 2
    assert stats["pending_review"] == 0


def test_approve_specific_attr(manager):
    decision = ReviewDecision(attr_ids=["attr-001"], reviewed_by="staff-1")
    approved = manager.approve("prod-001", decision)
    assert len(approved) == 1
    assert approved[0].attr_id == "attr-001"


def test_reject_all(manager):
    decision = ReviewDecision(reason="inaccurate", reviewed_by="staff-2")
    rejected = manager.reject("prod-001", decision)
    assert len(rejected) == 2
    assert all(i.status == "rejected" for i in rejected)
    assert all(i.rejected_reason == "inaccurate" for i in rejected)


def test_edit_and_approve(manager):
    decision = ReviewDecision(
        attr_ids=["attr-001"],
        edited_value="Navy Blue",
        reviewed_by="staff-3",
    )
    edited = manager.edit_and_approve("prod-001", decision)
    assert len(edited) == 1
    item = edited[0]
    assert item.proposed_value == "Navy Blue"
    assert item.source == "human"
    assert item.status == "approved"


def test_approve_unknown_entity_returns_empty(manager):
    decision = ReviewDecision()
    result = manager.approve("unknown-entity", decision)
    assert result == []


def test_audit_log_records_actions(manager):
    manager.approve("prod-001", ReviewDecision(reviewed_by="staff-1"))
    log = manager.audit_log()
    assert len(log) == 2
    assert all(e.action == "approved" for e in log)


def test_audit_log_filtered_by_entity(manager):
    manager.reject("prod-001", ReviewDecision(reason="test"))
    log = manager.audit_log(entity_id="prod-001")
    assert len(log) == 2
    no_log = manager.audit_log(entity_id="other-entity")
    assert no_log == []


def test_pagination(manager):
    items_page1 = manager.list_pending(skip=0, limit=1)
    items_page2 = manager.list_pending(skip=1, limit=1)
    assert len(items_page1) == 1
    assert len(items_page2) == 1
    assert items_page1[0].attr_id != items_page2[0].attr_id
