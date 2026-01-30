"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from crud_service.main import app


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
