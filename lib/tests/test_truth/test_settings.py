"""Tests for TruthLayerSettings (Issue #95)."""

import pytest
from holiday_peak_lib.config.settings import TruthLayerSettings


class TestTruthLayerSettings:
    def test_defaults(self, monkeypatch):
        for key in [
            "COSMOS_TRUTH_DATABASE",
            "EVENTHUB_TRUTH_NAMESPACE",
        ]:
            monkeypatch.delenv(key, raising=False)

        settings = TruthLayerSettings()
        assert settings.cosmos_truth_database is None
        assert settings.eventhub_truth_namespace is None
        assert settings.auto_approve_threshold == 0.95
        assert settings.human_review_threshold == 0.70

    def test_all_containers_present(self, monkeypatch):
        settings = TruthLayerSettings()
        expected = {
            "products", "attributes_truth", "attributes_proposed",
            "assets", "evidence", "schemas", "mappings", "audit", "config",
        }
        assert expected == set(settings.cosmos_truth_containers.values())

    def test_all_topics_present(self, monkeypatch):
        settings = TruthLayerSettings()
        expected = {
            "ingest-jobs", "gap-jobs", "enrichment-jobs",
            "writeback-jobs", "export-jobs",
        }
        assert expected == set(settings.eventhub_truth_topics.values())

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("COSMOS_TRUTH_DATABASE", "truth-db")
        monkeypatch.setenv("EVENTHUB_TRUTH_NAMESPACE", "ns-truth")
        monkeypatch.setenv("AUTO_APPROVE_THRESHOLD", "0.90")
        monkeypatch.setenv("HUMAN_REVIEW_THRESHOLD", "0.65")

        settings = TruthLayerSettings()
        assert settings.cosmos_truth_database == "truth-db"
        assert settings.eventhub_truth_namespace == "ns-truth"
        assert settings.auto_approve_threshold == 0.90
        assert settings.human_review_threshold == 0.65
