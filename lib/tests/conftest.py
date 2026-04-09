"""Pytest configuration and shared fixtures."""

from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture(autouse=True)
def normalize_foundry_env_for_lib_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep lib tests hermetic from ambient Foundry strict-mode flags."""
    # No GoF pattern applies — this fixture only normalizes ambient env per test.
    monkeypatch.delenv("FOUNDRY_STRICT_ENFORCEMENT", raising=False)
    monkeypatch.delenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP", raising=False)


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    client = AsyncMock()
    client.set = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value="test_value")
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=1)
    return client


@pytest.fixture
def mock_cosmos_client():
    """Mock Cosmos DB client for testing."""
    client = AsyncMock()
    database = AsyncMock()
    container = AsyncMock()
    container.upsert_item = AsyncMock(return_value={"id": "test", "value": "data"})
    container.read_item = AsyncMock(return_value={"id": "test", "value": "data"})
    container.query_items = AsyncMock(return_value=[{"id": "test"}])
    database.get_container_client = Mock(return_value=container)
    client.get_database_client = Mock(return_value=database)
    return client


@pytest.fixture
def mock_blob_client():
    """Mock Blob Storage client for testing."""
    client = AsyncMock()
    container = AsyncMock()
    container.upload_blob = AsyncMock(return_value=None)
    blob_mock = AsyncMock()
    blob_mock.readall = AsyncMock(return_value=b"test data")
    container.download_blob = AsyncMock(return_value=blob_mock)
    client.get_container_client = Mock(return_value=container)
    return client


@pytest.fixture
def sample_request():
    """Sample request payload for testing."""
    return {"query": "test query", "user_id": "user123", "context": {"key": "value"}}


@pytest.fixture
def sample_crm_account():
    """Sample CRM account data."""
    return {
        "account_id": "A123",
        "name": "Test Company",
        "region": "US-West",
        "industry": "Technology",
        "tier": "Enterprise",
    }


@pytest.fixture
def sample_crm_contact():
    """Sample CRM contact data."""
    return {
        "contact_id": "C456",
        "account_id": "A123",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
    }
