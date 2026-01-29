"""Tests for configuration models."""
import pytest
from holiday_peak_lib.config.settings import (
    MemorySettings,
    ServiceSettings,
    PostgresSettings,
)


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
        
        settings = MemorySettings()
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.cosmos_account_uri == "https://test.documents.azure.com"
        assert settings.cosmos_database == "test_db"
        assert settings.cosmos_container == "test_container"
        assert settings.blob_account_url == "https://test.blob.core.windows.net"
        assert settings.blob_container == "test_blob_container"

    def test_missing_required_env_raises(self, monkeypatch):
        """Test that missing required env vars raises error."""
        # Clear all relevant env vars
        for key in ["REDIS_URL", "COSMOS_ACCOUNT_URI", "COSMOS_DATABASE",
                    "COSMOS_CONTAINER", "BLOB_ACCOUNT_URL", "BLOB_CONTAINER"]:
            monkeypatch.delenv(key, raising=False)
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            MemorySettings()

    def test_redis_url_format(self, monkeypatch):
        """Test Redis URL format."""
        monkeypatch.setenv("REDIS_URL", "redis://user:pass@host:6379/0")
        monkeypatch.setenv("COSMOS_ACCOUNT_URI", "https://test.documents.azure.com")
        monkeypatch.setenv("COSMOS_DATABASE", "db")
        monkeypatch.setenv("COSMOS_CONTAINER", "container")
        monkeypatch.setenv("BLOB_ACCOUNT_URL", "https://test.blob.core.windows.net")
        monkeypatch.setenv("BLOB_CONTAINER", "container")
        
        settings = MemorySettings()
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
        
        settings = ServiceSettings()
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
        
        settings = ServiceSettings()
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
        
        settings = ServiceSettings()
        assert settings.monitor_connection_string is None


class TestPostgresSettings:
    """Test PostgresSettings configuration."""

    def test_create_from_env(self, monkeypatch):
        """Test creating PostgresSettings from environment variables."""
        monkeypatch.setenv(
            "POSTGRES_DSN",
            "postgresql://user:pass@localhost:5432/dbname"
        )
        
        settings = PostgresSettings()
        assert settings.postgres_dsn == "postgresql://user:pass@localhost:5432/dbname"
        assert "postgresql://" in settings.postgres_dsn

    def test_missing_postgres_dsn_raises(self, monkeypatch):
        """Test that missing Postgres DSN raises error."""
        monkeypatch.delenv("POSTGRES_DSN", raising=False)
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            PostgresSettings()

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
            settings = PostgresSettings()
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
        
        memory_settings = MemorySettings()
        service_settings = ServiceSettings()
        postgres_settings = PostgresSettings()
        
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
        
        settings = MemorySettings()
        original_url = settings.redis_url
        
        # Changing env var shouldn't affect existing instance
        monkeypatch.setenv("REDIS_URL", "redis://changed:6379")
        assert settings.redis_url == original_url
