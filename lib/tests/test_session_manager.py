"""Tests for session_manager: smart session continuity logic."""

import json
import time
from unittest.mock import AsyncMock

import pytest
from holiday_peak_lib.agents.memory.session_manager import (
    SessionDecision,
    SessionSummary,
    build_session_summary,
    compute_keyword_overlap,
    evaluate_session_continuity,
    extract_keywords,
    persist_full_session,
    store_summary,
)


class TestExtractKeywords:
    def test_basic_extraction(self):
        text = "compute the shipping ETA for tracking order"
        keywords = extract_keywords(text)
        assert "compute" in keywords
        assert "shipping" in keywords
        assert "tracking" in keywords
        # Stop words removed
        assert "the" not in keywords
        assert "for" not in keywords

    def test_empty_text(self):
        assert extract_keywords("") == []
        assert extract_keywords(None) == []

    def test_max_keywords_cap(self):
        text = " ".join(f"keyword{i}" for i in range(20))
        keywords = extract_keywords(text, max_keywords=5)
        assert len(keywords) == 5

    def test_deduplication(self):
        text = "product product product category category"
        keywords = extract_keywords(text)
        assert keywords.count("product") == 1
        assert keywords.count("category") == 1


class TestComputeKeywordOverlap:
    def test_full_overlap(self):
        assert compute_keyword_overlap(["eta", "shipping"], ["eta", "shipping"]) == 1.0

    def test_no_overlap(self):
        assert compute_keyword_overlap(["eta", "shipping"], ["inventory", "stock"]) == 0.0

    def test_partial_overlap(self):
        overlap = compute_keyword_overlap(
            ["eta", "shipping", "tracking"], ["eta", "delivery", "tracking"]
        )
        # intersection={eta,tracking}, union={eta,shipping,tracking,delivery}
        assert abs(overlap - 2 / 4) < 0.01

    def test_empty_lists(self):
        assert compute_keyword_overlap([], ["something"]) == 0.0
        assert compute_keyword_overlap(["something"], []) == 0.0
        assert compute_keyword_overlap([], []) == 0.0


class TestEvaluateSessionContinuity:
    @pytest.mark.asyncio
    async def test_no_hot_memory_returns_fresh(self):
        decision = await evaluate_session_continuity(
            None, None, {"query": "test"}, service="svc", entity_id="ent1"
        )
        assert decision.continue_session is False
        assert decision.session_id == "ent1"

    @pytest.mark.asyncio
    async def test_no_summary_in_redis_returns_fresh(self):
        hot = AsyncMock()
        hot.get = AsyncMock(return_value=None)
        decision = await evaluate_session_continuity(
            hot, None, {"query": "test"}, service="svc", entity_id="ent1"
        )
        assert decision.continue_session is False

    @pytest.mark.asyncio
    async def test_stale_summary_returns_fresh(self):
        hot = AsyncMock()
        summary = SessionSummary(
            session_id="svc:ent1:old",
            service="svc",
            entity_id="ent1",
            topic_keywords=["shipping", "tracking"],
            message_count=2,
            last_epoch=time.time() - 3600,  # 1 hour ago = stale
            summary_text="prior response",
        )
        hot.get = AsyncMock(return_value=json.dumps(summary.__dict__))
        decision = await evaluate_session_continuity(
            hot, None, {"query": "shipping update"}, service="svc", entity_id="ent1"
        )
        assert decision.continue_session is False

    @pytest.mark.asyncio
    async def test_high_message_count_returns_fresh(self):
        hot = AsyncMock()
        summary = SessionSummary(
            session_id="svc:ent1:old",
            service="svc",
            entity_id="ent1",
            topic_keywords=["shipping", "tracking"],
            message_count=25,  # exceeds threshold of 20
            last_epoch=time.time(),
            summary_text="prior response",
        )
        hot.get = AsyncMock(return_value=json.dumps(summary.__dict__))
        decision = await evaluate_session_continuity(
            hot, None, {"query": "shipping update"}, service="svc", entity_id="ent1"
        )
        assert decision.continue_session is False

    @pytest.mark.asyncio
    async def test_keyword_overlap_continues_session(self):
        hot = AsyncMock()
        warm = AsyncMock()
        summary = SessionSummary(
            session_id="svc:ent1:123",
            service="svc",
            entity_id="ent1",
            topic_keywords=["shipping", "tracking", "delivery", "eta"],
            message_count=3,
            last_epoch=time.time() - 60,  # 1 min ago = fresh
            summary_text="computed ETA for shipment",
        )
        hot.get = AsyncMock(return_value=json.dumps(summary.__dict__))
        warm.read = AsyncMock(
            return_value={
                "foundry_session_state": {"session_id": "foundry-abc"},
            }
        )
        decision = await evaluate_session_continuity(
            hot,
            warm,
            {"query": "update shipping eta tracking"},
            service="svc",
            entity_id="ent1",
        )
        assert decision.continue_session is True
        assert decision.session_id == "svc:ent1:123"
        assert decision.foundry_session_state == {"session_id": "foundry-abc"}

    @pytest.mark.asyncio
    async def test_keyword_divergence_returns_fresh(self):
        hot = AsyncMock()
        summary = SessionSummary(
            session_id="svc:ent1:123",
            service="svc",
            entity_id="ent1",
            topic_keywords=["shipping", "tracking", "delivery"],
            message_count=3,
            last_epoch=time.time() - 60,
            summary_text="shipping related",
        )
        hot.get = AsyncMock(return_value=json.dumps(summary.__dict__))
        # Completely different topic
        decision = await evaluate_session_continuity(
            hot,
            None,
            {"query": "inventory stock replenishment forecast"},
            service="svc",
            entity_id="ent1",
        )
        assert decision.continue_session is False

    @pytest.mark.asyncio
    async def test_cosmos_read_failure_still_continues(self):
        """If Cosmos is unavailable, still continue but without session state."""
        hot = AsyncMock()
        warm = AsyncMock()
        summary = SessionSummary(
            session_id="svc:ent1:123",
            service="svc",
            entity_id="ent1",
            topic_keywords=["shipping", "eta", "tracking"],
            message_count=2,
            last_epoch=time.time(),
            summary_text="prior",
        )
        hot.get = AsyncMock(return_value=json.dumps(summary.__dict__))
        warm.read = AsyncMock(side_effect=Exception("Cosmos unavailable"))
        decision = await evaluate_session_continuity(
            hot,
            warm,
            {"query": "shipping eta tracking update"},
            service="svc",
            entity_id="ent1",
        )
        assert decision.continue_session is True
        assert decision.foundry_session_state is None


class TestBuildSessionSummary:
    def test_builds_summary_from_interaction(self):
        summary = build_session_summary(
            session_id="svc:ent1:123",
            service="svc",
            entity_id="ent1",
            messages=[
                {"role": "system", "content": "You are a logistics assistant"},
                {"role": "user", "content": "What is the ETA for shipment TRK-456?"},
            ],
            result={"content": "The estimated delivery is 3 days from now."},
        )
        assert summary.session_id == "svc:ent1:123"
        assert summary.message_count == 2
        assert "estimated" in summary.summary_text or "delivery" in summary.summary_text
        assert len(summary.topic_keywords) > 0

    def test_merges_with_prior_summary(self):
        prior = SessionSummary(
            session_id="svc:ent1:123",
            service="svc",
            entity_id="ent1",
            topic_keywords=["shipping", "eta"],
            message_count=2,
            last_epoch=time.time() - 120,
            summary_text="old",
        )
        summary = build_session_summary(
            session_id="svc:ent1:123",
            service="svc",
            entity_id="ent1",
            messages=[{"role": "user", "content": "update delivery date"}],
            result={"content": "delivery rescheduled"},
            prior_summary=prior,
        )
        assert summary.message_count == 3  # 2 prior + 1 new
        assert "shipping" in summary.topic_keywords  # Preserved from prior

    def test_truncates_long_result(self):
        summary = build_session_summary(
            session_id="s1",
            service="svc",
            entity_id="e1",
            messages=[],
            result={"content": "x" * 500},
        )
        assert len(summary.summary_text) <= 203  # 200 + "..."


class TestStoreSummary:
    @pytest.mark.asyncio
    async def test_stores_to_redis(self):
        hot = AsyncMock()
        hot.set = AsyncMock()
        summary = SessionSummary(
            session_id="svc:ent1:123",
            service="svc",
            entity_id="ent1",
            topic_keywords=["test"],
            message_count=1,
            last_epoch=time.time(),
            summary_text="hello",
        )
        await store_summary(hot, summary, ttl_seconds=1800)
        hot.set.assert_called_once()
        call_kwargs = hot.set.call_args[1]
        assert "session_summary:" in call_kwargs["key"]
        assert call_kwargs["ttl_seconds"] == 1800

    @pytest.mark.asyncio
    async def test_none_hot_memory_noop(self):
        await store_summary(
            None,
            SessionSummary(
                session_id="x",
                service="s",
                entity_id="e",
                topic_keywords=[],
                message_count=0,
                last_epoch=0,
                summary_text="",
            ),
        )


class TestPersistFullSession:
    @pytest.mark.asyncio
    async def test_persists_to_cosmos(self):
        warm = AsyncMock()
        warm.upsert = AsyncMock()
        await persist_full_session(
            warm,
            session_id="svc:ent1:123",
            service="svc",
            entity_id="ent1",
            foundry_session_state={"session_id": "foundry-abc"},
            messages=[{"role": "user", "content": "test"}],
            summary_text="test summary",
        )
        warm.upsert.assert_called_once()
        doc = warm.upsert.call_args[0][0]
        assert doc["id"] == "svc:ent1:123"
        assert doc["foundry_session_state"] == {"session_id": "foundry-abc"}

    @pytest.mark.asyncio
    async def test_none_warm_memory_noop(self):
        await persist_full_session(
            None,
            session_id="x",
            service="s",
            entity_id="e",
            foundry_session_state={"id": "test"},
            messages=[],
            summary_text="",
        )

    @pytest.mark.asyncio
    async def test_none_session_state_noop(self):
        warm = AsyncMock()
        await persist_full_session(
            warm,
            session_id="x",
            service="s",
            entity_id="e",
            foundry_session_state=None,
            messages=[],
            summary_text="",
        )
        warm.upsert.assert_not_called()
