"""Test configuration and fixtures."""

import os

# Set required environment variables BEFORE importing crud_service modules.
# This prevents pydantic Settings validation errors during test collection.
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("EVENT_HUB_NAMESPACE", "test-namespace.servicebus.windows.net")
os.environ.setdefault("KEY_VAULT_URI", "https://test-vault.vault.azure.net/")
os.environ.setdefault("REDIS_HOST", "localhost")

import pytest  # noqa: E402
from crud_service.config.settings import get_settings  # noqa: E402
from crud_service.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear the Settings lru_cache before each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_cosmos_db(monkeypatch):
    """Mock Cosmos DB for testing."""
    # TODO: Implement Cosmos DB mock
    pass


@pytest.fixture
def mock_event_hub(monkeypatch):
    """Mock Event Hubs for testing."""
    # TODO: Implement Event Hubs mock
    pass


@pytest.fixture
def mock_auth_token():
    """Mock JWT token for authenticated requests."""
    # TODO: Generate test JWT token
    return "Bearer test_token"
