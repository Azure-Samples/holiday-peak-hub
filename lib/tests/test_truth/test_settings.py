"""Tests for TruthLayerSettings (Issue #95).

Validates that the Pydantic ``TruthLayerSettings`` class exposes the
expected Cosmos DB container names, Event Hub topic names, feature
toggles, and supports environment-variable overrides via the
``TRUTH_`` prefix.
"""

import pytest
from holiday_peak_lib.config.settings import TruthLayerSettings


class TestTruthLayerSettings:
    def test_defaults(self, monkeypatch):
        """Default values are sensible when no env vars are set."""
        # Clear any env vars that could leak into the test
        for key in [
            "TRUTH_AUTO_APPROVE_THRESHOLD",
            "TRUTH_ENRICHMENT_ENABLED",
        ]:
            monkeypatch.delenv(key, raising=False)

        settings = TruthLayerSettings()
        assert settings.auto_approve_threshold == 0.85
        assert settings.enrichment_enabled is True
        assert settings.writeback_enabled is False

    def test_all_containers_present(self):
        """All expected Cosmos DB container fields exist with defaults."""
        settings = TruthLayerSettings()
        expected = {
            "products",
            "attributes_truth",
            "attributes_proposed",
            "schemas",
            "mappings",
            "audit",
            "config",
            "relationships",
            "completeness",
        }
        container_fields = {
            k: v
            for k, v in settings.model_dump().items()
            if k.startswith("cosmos_") and k.endswith("_container")
        }
        assert expected == set(container_fields.values())

    def test_all_topics_present(self):
        """All expected Event Hub topic fields exist with defaults."""
        settings = TruthLayerSettings()
        expected = {
            "enrichment-jobs",
            "completeness-jobs",
            "export-jobs",
            "hitl-jobs",
            "ingestion-notifications",
        }
        topic_fields = {
            k: v
            for k, v in settings.model_dump().items()
            if k.startswith("eventhub_")
            and k.endswith("_jobs")
            or k.startswith("eventhub_")
            and k.endswith("_notifications")
        }
        assert expected == set(topic_fields.values())

    def test_from_env(self, monkeypatch):
        """Environment variables with TRUTH_ prefix override defaults."""
        monkeypatch.setenv("TRUTH_AUTO_APPROVE_THRESHOLD", "0.90")
        monkeypatch.setenv("TRUTH_ENRICHMENT_ENABLED", "false")
        monkeypatch.setenv("TRUTH_MAX_ENRICHMENT_RETRIES", "5")

        settings = TruthLayerSettings()
        assert settings.auto_approve_threshold == 0.90
        assert settings.enrichment_enabled is False
        assert settings.max_enrichment_retries == 5
