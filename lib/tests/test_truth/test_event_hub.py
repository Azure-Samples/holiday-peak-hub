"""Tests for truth-layer Event Hub helpers (Issue #94)."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from holiday_peak_lib.truth.event_hub import (
    TRUTH_LAYER_TOPICS,
    TruthJobPublisher,
    build_truth_layer_subscriptions,
)
from holiday_peak_lib.utils.event_hub import EventHubSubscription


class TestTruthLayerTopics:
    def test_all_five_topics_present(self):
        expected = {"ingest", "gap", "enrichment", "writeback", "export"}
        assert expected == set(TRUTH_LAYER_TOPICS.keys())

    def test_topic_values_match_event_hub_names(self):
        assert TRUTH_LAYER_TOPICS["ingest"] == "ingest-jobs"
        assert TRUTH_LAYER_TOPICS["export"] == "export-jobs"


class TestTruthJobPublisher:
    def _make_publisher(self, producer_mock):
        return TruthJobPublisher(
            connection_string="Endpoint=sb://t/;SharedAccessKeyName=k;SharedAccessKey=v",
            eventhub_name="ingest-jobs",
            producer_factory=lambda cs, eh: producer_mock,
        )

    @pytest.mark.asyncio
    async def test_publish_sends_event(self):
        batch_mock = MagicMock()
        batch_mock.add = MagicMock()

        producer_mock = AsyncMock()
        producer_mock.__aenter__ = AsyncMock(return_value=producer_mock)
        producer_mock.__aexit__ = AsyncMock(return_value=False)
        producer_mock.create_batch = AsyncMock(return_value=batch_mock)
        producer_mock.send_batch = AsyncMock()

        pub = self._make_publisher(producer_mock)
        await pub.publish("ingest_requested", {"product_id": "p-1"})

        producer_mock.create_batch.assert_called_once()
        producer_mock.send_batch.assert_called_once_with(batch_mock)

        # Verify event payload
        event_data = batch_mock.add.call_args[0][0]
        raw_body = b"".join(event_data.body)
        payload = json.loads(raw_body)
        assert payload["event_type"] == "ingest_requested"
        assert payload["data"]["product_id"] == "p-1"

    def test_eventhub_name_set(self):
        pub = TruthJobPublisher(
            connection_string="Endpoint=sb://t/;SharedAccessKeyName=k;SharedAccessKey=v",
            eventhub_name="gap-jobs",
        )
        assert pub._eventhub_name == "gap-jobs"


class TestBuildTruthLayerSubscriptions:
    def test_all_topics_when_none(self):
        subs = build_truth_layer_subscriptions()
        assert len(subs) == 5
        names = {s.eventhub_name for s in subs}
        assert names == set(TRUTH_LAYER_TOPICS.values())

    def test_subset_of_topics(self):
        subs = build_truth_layer_subscriptions(topics=["ingest", "export"])
        assert len(subs) == 2
        names = {s.eventhub_name for s in subs}
        assert names == {"ingest-jobs", "export-jobs"}

    def test_custom_consumer_group(self):
        subs = build_truth_layer_subscriptions(consumer_group="truth-cg")
        assert all(s.consumer_group == "truth-cg" for s in subs)

    def test_returns_event_hub_subscription_instances(self):
        subs = build_truth_layer_subscriptions()
        assert all(isinstance(s, EventHubSubscription) for s in subs)

    def test_raw_eventhub_name_passthrough(self):
        subs = build_truth_layer_subscriptions(topics=["ingest-jobs"])
        assert subs[0].eventhub_name == "ingest-jobs"
