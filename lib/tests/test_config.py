"""Tests for configuration models."""

import pytest
from holiday_peak_lib.config.settings import (
    MemorySettings,
    PostgresSettings,
    ServiceSettings,
    TruthLayerSettings,
)
from holiday_peak_lib.config.tenant_config import TenantConfig


def _memory_settings() -> MemorySettings:
    return MemorySettings(_env_file=None)


def _service_settings() -> ServiceSettings:
    return ServiceSettings(_env_file=None)


def _postgres_settings() -> PostgresSettings:
    return PostgresSettings(_env_file=None)


def _truth_layer_settings() -> TruthLayerSettings:
    return TruthLayerSettings(_env_file=None)


class TestMemorySettings:
    """Test MemorySettings configuration."""

    def test_create_from_env(self, monkeypatch):
        """Test creating MemorySettings from environment variables."""
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
        monkeypatch.setenv("COSMOS_ACCOUNT_URI", "https://test.documents.azure.com")
        monkeypatch.setenv("COSMOS_DATABASE", "test_db")
        monkeypatch.setenv("COSMOS_CONTAINER", "test_container")
        monkeypatch.setenv("BLOB_ACCOUNT_URL", "https://test.blob.core.windows.net")
        monkeypatch.setenv("BLOB_CONTAINER", "test_blob_container")

        settings = _memory_settings()
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.cosmos_account_uri == "https://test.documents.azure.com"
        assert settings.cosmos_database == "test_db"
        assert settings.cosmos_container == "test_container"
        assert settings.blob_account_url == "https://test.blob.core.windows.net"
        assert settings.blob_container == "test_blob_container"

    def test_missing_required_env_uses_defaults(self, monkeypatch):
        """Test that missing env vars produce None defaults (fields are optional)."""
        # Clear all relevant env vars
        for key in [
            "REDIS_URL",
            "COSMOS_ACCOUNT_URI",
            "COSMOS_DATABASE",
            "COSMOS_CONTAINER",
            "BLOB_ACCOUNT_URL",
            "BLOB_CONTAINER",
        ]:
            monkeypatch.delenv(key, raising=False)

        settings = _memory_settings()
        assert settings.redis_url is None
        assert settings.cosmos_account_uri is None

    def test_redis_url_format(self, monkeypatch):
        """Test Redis URL format."""
        monkeypatch.setenv("REDIS_URL", "redis://user:pass@host:6379/0")
        monkeypatch.setenv("COSMOS_ACCOUNT_URI", "https://test.documents.azure.com")
        monkeypatch.setenv("COSMOS_DATABASE", "db")
        monkeypatch.setenv("COSMOS_CONTAINER", "container")
        monkeypatch.setenv("BLOB_ACCOUNT_URL", "https://test.blob.core.windows.net")
        monkeypatch.setenv("BLOB_CONTAINER", "container")

        settings = _memory_settings()
        assert "redis://" in settings.redis_url
        assert "6379" in settings.redis_url


class TestServiceSettings:
    """Test ServiceSettings configuration."""

    def test_create_from_env(self, monkeypatch):
        """Test creating ServiceSettings from environment variables."""
        monkeypatch.setenv("SERVICE_NAME", "test-service")
        monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://search.azure.com")
        monkeypatch.setenv("AI_SEARCH_INDEX", "test-index")
        monkeypatch.setenv("AI_SEARCH_KEY", "test-key-123")
        monkeypatch.setenv("EVENT_HUB_NAMESPACE", "test-namespace")
        monkeypatch.setenv("EVENT_HUB_NAME", "test-hub")

        settings = _service_settings()
        assert settings.service_name == "test-service"
        assert settings.ai_search_endpoint == "https://search.azure.com"
        assert settings.ai_search_index == "test-index"
        assert settings.ai_search_key == "test-key-123"
        assert settings.event_hub_namespace == "test-namespace"
        assert settings.event_hub_name == "test-hub"

    def test_optional_monitor_connection_string(self, monkeypatch):
        """Test optional monitor connection string."""
        monkeypatch.setenv("SERVICE_NAME", "test-service")
        monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://search.azure.com")
        monkeypatch.setenv("AI_SEARCH_INDEX", "test-index")
        monkeypatch.setenv("AI_SEARCH_KEY", "test-key-123")
        monkeypatch.setenv("EVENT_HUB_NAMESPACE", "test-namespace")
        monkeypatch.setenv("EVENT_HUB_NAME", "test-hub")
        monkeypatch.setenv("AZURE_MONITOR_CONNECTION_STRING", "InstrumentationKey=abc")

        settings = _service_settings()
        assert settings.monitor_connection_string == "InstrumentationKey=abc"

    def test_monitor_connection_string_defaults_to_none(self, monkeypatch):
        """Test monitor connection string defaults to None."""
        monkeypatch.setenv("SERVICE_NAME", "test-service")
        monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://search.azure.com")
        monkeypatch.setenv("AI_SEARCH_INDEX", "test-index")
        monkeypatch.setenv("AI_SEARCH_KEY", "test-key-123")
        monkeypatch.setenv("EVENT_HUB_NAMESPACE", "test-namespace")
        monkeypatch.setenv("EVENT_HUB_NAME", "test-hub")
        monkeypatch.delenv("AZURE_MONITOR_CONNECTION_STRING", raising=False)

        settings = _service_settings()
        assert settings.monitor_connection_string is None


class TestPostgresSettings:
    """Test PostgresSettings configuration."""

    def test_create_from_env(self, monkeypatch):
        """Test creating PostgresSettings from environment variables."""
        monkeypatch.setenv("POSTGRES_DSN", "postgresql://user:pass@localhost:5432/dbname")

        settings = _postgres_settings()
        assert settings.postgres_dsn == "postgresql://user:pass@localhost:5432/dbname"
        assert "postgresql://" in settings.postgres_dsn

    def test_missing_postgres_dsn_raises(self, monkeypatch):
        """Test that missing Postgres DSN raises error."""
        monkeypatch.delenv("POSTGRES_DSN", raising=False)

        with pytest.raises(Exception):  # Pydantic ValidationError
            _postgres_settings()

    def test_postgres_dsn_format_validation(self, monkeypatch):
        """Test various Postgres DSN formats."""
        valid_dsns = [
            "postgresql://localhost/mydb",
            "postgresql://user@localhost/mydb",
            "postgresql://user:secret@localhost/mydb",
            "postgresql://user:secret@localhost:5433/mydb",
            "postgresql://host1:123,host2:456/somedb",
        ]

        for dsn in valid_dsns:
            monkeypatch.setenv("POSTGRES_DSN", dsn)
            settings = _postgres_settings()
            assert settings.postgres_dsn == dsn


class TestSettingsIntegration:
    """Test settings integration and usage patterns."""

    def test_all_settings_from_env(self, monkeypatch):
        """Test creating all settings from environment."""
        # Set all environment variables
        env_vars = {
            # Memory
            "REDIS_URL": "redis://localhost:6379",
            "COSMOS_ACCOUNT_URI": "https://test.documents.azure.com",
            "COSMOS_DATABASE": "test_db",
            "COSMOS_CONTAINER": "test_container",
            "BLOB_ACCOUNT_URL": "https://test.blob.core.windows.net",
            "BLOB_CONTAINER": "test_container",
            # Service
            "SERVICE_NAME": "test-service",
            "AI_SEARCH_ENDPOINT": "https://search.azure.com",
            "AI_SEARCH_INDEX": "test-index",
            "AI_SEARCH_KEY": "test-key",
            "EVENT_HUB_NAMESPACE": "test-namespace",
            "EVENT_HUB_NAME": "test-hub",
            # Postgres
            "POSTGRES_DSN": "postgresql://localhost/test",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        memory_settings = _memory_settings()
        service_settings = _service_settings()
        postgres_settings = _postgres_settings()

        assert memory_settings.redis_url is not None
        assert service_settings.service_name == "test-service"
        assert postgres_settings.postgres_dsn is not None

    def test_settings_immutability(self, monkeypatch):
        """Test that settings are properly configured."""
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
        monkeypatch.setenv("COSMOS_ACCOUNT_URI", "https://test.documents.azure.com")
        monkeypatch.setenv("COSMOS_DATABASE", "db")
        monkeypatch.setenv("COSMOS_CONTAINER", "container")
        monkeypatch.setenv("BLOB_ACCOUNT_URL", "https://test.blob.core.windows.net")
        monkeypatch.setenv("BLOB_CONTAINER", "container")

        settings = _memory_settings()
        original_url = settings.redis_url

        # Changing env var shouldn't affect existing instance
        monkeypatch.setenv("REDIS_URL", "redis://changed:6379")
        assert settings.redis_url == original_url


class TestTruthLayerSettings:
    """Test TruthLayerSettings configuration."""

    def test_default_values(self):
        """Test that TruthLayerSettings has correct default values."""
        settings = _truth_layer_settings()

        # Cosmos DB containers
        assert settings.cosmos_products_container == "products"
        assert settings.cosmos_attributes_truth_container == "attributes_truth"
        assert settings.cosmos_attributes_proposed_container == "attributes_proposed"
        assert settings.cosmos_schemas_container == "schemas"
        assert settings.cosmos_mappings_container == "mappings"
        assert settings.cosmos_audit_container == "audit"
        assert settings.cosmos_config_container == "config"
        assert settings.cosmos_relationships_container == "relationships"
        assert settings.cosmos_completeness_container == "completeness"

        # Event Hub topics
        assert settings.eventhub_enrichment_jobs == "enrichment-jobs"
        assert settings.eventhub_completeness_jobs == "completeness-jobs"
        assert settings.eventhub_export_jobs == "export-jobs"
        assert settings.eventhub_hitl_jobs == "hitl-jobs"
        assert settings.eventhub_ingestion_notifications == "ingestion-notifications"

        # Feature toggles - production-safe defaults
        assert settings.enrichment_enabled is True
        assert settings.auto_approve_enabled is True
        assert settings.auto_approve_threshold == 0.85
        assert settings.writeback_enabled is False
        assert settings.evidence_extraction_enabled is False

        # Operational
        assert settings.max_enrichment_retries == 3
        assert settings.completeness_cache_ttl_seconds == 300

    def test_env_var_override(self, monkeypatch):
        """Test that env vars with TRUTH_ prefix override defaults."""
        monkeypatch.setenv("TRUTH_COSMOS_PRODUCTS_CONTAINER", "custom_products")
        monkeypatch.setenv("TRUTH_EVENTHUB_ENRICHMENT_JOBS", "my-enrichment-topic")
        monkeypatch.setenv("TRUTH_ENRICHMENT_ENABLED", "false")
        monkeypatch.setenv("TRUTH_WRITEBACK_ENABLED", "true")
        monkeypatch.setenv("TRUTH_AUTO_APPROVE_THRESHOLD", "0.95")
        monkeypatch.setenv("TRUTH_MAX_ENRICHMENT_RETRIES", "5")
        monkeypatch.setenv("TRUTH_COMPLETENESS_CACHE_TTL_SECONDS", "600")

        settings = _truth_layer_settings()

        assert settings.cosmos_products_container == "custom_products"
        assert settings.eventhub_enrichment_jobs == "my-enrichment-topic"
        assert settings.enrichment_enabled is False
        assert settings.writeback_enabled is True
        assert settings.auto_approve_threshold == 0.95
        assert settings.max_enrichment_retries == 5
        assert settings.completeness_cache_ttl_seconds == 600

    def test_production_safe_defaults(self):
        """Verify writeback and evidence extraction are off by default."""
        settings = _truth_layer_settings()
        assert settings.writeback_enabled is False
        assert settings.evidence_extraction_enabled is False

    def test_env_prefix_isolation(self, monkeypatch):
        """Test that unprefixed env vars do not affect TruthLayerSettings."""
        monkeypatch.setenv("COSMOS_PRODUCTS_CONTAINER", "should_be_ignored")
        monkeypatch.setenv("ENRICHMENT_ENABLED", "false")

        settings = _truth_layer_settings()

        assert settings.cosmos_products_container == "products"
        assert settings.enrichment_enabled is True


class TestTenantConfig:
    """Test TenantConfig model."""

    def test_default_values(self):
        """Verify all defaults match the model definition."""
        cfg = TenantConfig(tenant_id="t-001")
        assert cfg.tenant_id == "t-001"
        assert cfg.auto_approve_threshold == 0.85
        assert cfg.enrichment_enabled is True
        assert cfg.writeback_enabled is False
        assert cfg.default_protocol == "acp"
        assert cfg.schema_version == "v1"
        assert cfg.allowed_enrichment_sources == ["ai", "manual"]
        assert cfg.completeness_weights == {}
        assert cfg.hitl_required_fields == []

    def test_custom_values(self):
        """Verify custom construction works."""
        cfg = TenantConfig(
            tenant_id="t-002",
            auto_approve_threshold=0.5,
            enrichment_enabled=False,
            writeback_enabled=True,
            default_protocol="rest",
            schema_version="v2",
            allowed_enrichment_sources=["manual"],
            completeness_weights={"title": 0.3, "description": 0.7},
            hitl_required_fields=["brand"],
        )
        assert cfg.tenant_id == "t-002"
        assert cfg.auto_approve_threshold == 0.5
        assert cfg.enrichment_enabled is False
        assert cfg.writeback_enabled is True
        assert cfg.default_protocol == "rest"
        assert cfg.schema_version == "v2"
        assert cfg.allowed_enrichment_sources == ["manual"]
        assert cfg.completeness_weights == {"title": 0.3, "description": 0.7}
        assert cfg.hitl_required_fields == ["brand"]

    def test_boundary_threshold_values(self):
        """Boundary values 0.0 and 1.0 should be accepted."""
        assert (
            TenantConfig(tenant_id="t-003", auto_approve_threshold=0.0).auto_approve_threshold
            == 0.0
        )
        assert (
            TenantConfig(tenant_id="t-003", auto_approve_threshold=1.0).auto_approve_threshold
            == 1.0
        )

    def test_invalid_threshold_rejected(self):
        """Values outside 0-1 must raise ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TenantConfig(tenant_id="t-bad", auto_approve_threshold=-0.1)
        with pytest.raises(ValidationError):
            TenantConfig(tenant_id="t-bad", auto_approve_threshold=1.01)

    def test_to_cosmos_document(self):
        """Verify serialization sets id and partition_key."""
        cfg = TenantConfig(tenant_id="t-cosmos")
        doc = cfg.to_cosmos_document()
        assert doc["id"] == "t-cosmos"
        assert doc["partition_key"] == "t-cosmos"
        assert doc["tenant_id"] == "t-cosmos"
        assert doc["auto_approve_threshold"] == 0.85
