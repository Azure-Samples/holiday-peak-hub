"""Test configuration and fixtures."""

import copy
import os
import re
from unittest.mock import AsyncMock

# Set required environment variables BEFORE importing crud_service modules.
# This prevents pydantic Settings validation errors during test collection.
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("EVENT_HUB_NAMESPACE", "test-namespace.servicebus.windows.net")
os.environ.setdefault("KEY_VAULT_URI", "https://test-vault.vault.azure.net/")
os.environ.setdefault("REDIS_HOST", "localhost")

import pytest  # noqa: E402
from crud_service.auth import User, get_current_user  # noqa: E402
from crud_service.config.settings import get_settings  # noqa: E402
from crud_service.main import app  # noqa: E402
from crud_service.repositories.base import BaseRepository  # noqa: E402
from crud_service.routes import orders as orders_routes  # noqa: E402
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
    """Mock repository storage with an in-memory backend for tests."""
    store: dict[str, dict[str, dict]] = {
        "products": {
            "test-product": {
                "id": "test-product",
                "name": "Test Product",
                "description": "A test product",
                "price": 99.99,
                "category_id": "electronics",
                "in_stock": True,
            },
            "test-laptop": {
                "id": "test-laptop",
                "name": "Test Laptop",
                "description": "Laptop for testing",
                "price": 999.99,
                "category_id": "electronics",
                "in_stock": True,
            },
            "test-shoes": {
                "id": "test-shoes",
                "name": "Running Shoes",
                "description": "Shoes for testing",
                "price": 89.99,
                "category_id": "fashion",
                "in_stock": True,
            },
        },
        "cart": {},
        "orders": {},
    }

    def _get_items(container_name: str) -> list[dict]:
        container = store.setdefault(container_name, {})
        return [copy.deepcopy(item) for item in container.values()]

    def _partition_key(item: dict) -> str:
        return BaseRepository._extract_partition_key(item)

    async def _query(self, query: str, parameters=None, partition_key=None):
        parameter_map = {p["name"]: p["value"] for p in (parameters or [])}
        items = _get_items(self.container_name)

        if partition_key is not None:
            items = [item for item in items if _partition_key(item) == str(partition_key)]

        where_clause = ""
        where_match = re.search(r"WHERE\s+(.*?)\s*(ORDER BY|OFFSET|LIMIT|$)", query, re.IGNORECASE)
        if where_match:
            where_clause = where_match.group(1).strip()

        if where_clause:
            items = [
                item
                for item in items
                if BaseRepository._matches_where(item, where_clause, parameter_map)
            ]

        order_match = re.search(r"ORDER BY\s+c\.(\w+)\s+(ASC|DESC)", query, re.IGNORECASE)
        if order_match:
            order_field = order_match.group(1)
            reverse = order_match.group(2).upper() == "DESC"
            items = sorted(items, key=lambda item: item.get(order_field, ""), reverse=reverse)

        limit_match = re.search(r"LIMIT\s+(@\w+|\d+)", query, re.IGNORECASE)
        if limit_match:
            limit_token = limit_match.group(1)
            limit_value = (
                int(parameter_map.get(limit_token, len(items)))
                if limit_token.startswith("@")
                else int(limit_token)
            )
            items = items[:limit_value]

        return items

    async def _get_by_id(self, item_id: str, partition_key=None):
        item = store.setdefault(self.container_name, {}).get(item_id)
        if item is None:
            return None
        if partition_key is not None and _partition_key(item) != str(partition_key):
            return None
        return copy.deepcopy(item)

    async def _create(self, item: dict):
        store.setdefault(self.container_name, {})[item["id"]] = copy.deepcopy(item)
        return copy.deepcopy(item)

    async def _update(self, item: dict):
        store.setdefault(self.container_name, {})[item["id"]] = copy.deepcopy(item)
        return copy.deepcopy(item)

    async def _delete(self, item_id: str, partition_key=None):
        container = store.setdefault(self.container_name, {})
        if item_id in container:
            if partition_key is None or _partition_key(container[item_id]) == str(partition_key):
                container.pop(item_id, None)

    monkeypatch.setattr(BaseRepository, "query", _query, raising=True)
    monkeypatch.setattr(BaseRepository, "get_by_id", _get_by_id, raising=True)
    monkeypatch.setattr(BaseRepository, "create", _create, raising=True)
    monkeypatch.setattr(BaseRepository, "update", _update, raising=True)
    monkeypatch.setattr(BaseRepository, "delete", _delete, raising=True)

    return {"store": store}


@pytest.fixture
def mock_event_hub(monkeypatch):
    """Mock Event Hubs for testing."""
    published_events: list[dict] = []

    async def _publish_order_created(order: dict, **kwargs):
        published_events.append(
            {
                "topic": "order-events",
                "event_type": "OrderCreated",
                "data": copy.deepcopy(order),
                "kwargs": copy.deepcopy(kwargs),
            }
        )

    async def _publish(topic: str, event_type: str, data: dict, **kwargs):
        published_events.append(
            {
                "topic": topic,
                "event_type": event_type,
                "data": copy.deepcopy(data),
                "kwargs": copy.deepcopy(kwargs),
            }
        )

    monkeypatch.setattr(
        orders_routes.event_publisher,
        "publish_order_created",
        AsyncMock(side_effect=_publish_order_created),
    )
    monkeypatch.setattr(
        orders_routes.event_publisher,
        "publish",
        AsyncMock(side_effect=_publish),
    )

    return published_events


@pytest.fixture
def mock_auth_token():
    """Override auth dependency and return request headers for authenticated tests."""

    async def _override_user():
        return User(
            user_id="test-user",
            email="test-user@example.com",
            name="Test User",
            roles=["customer"],
        )

    app.dependency_overrides[get_current_user] = _override_user
    try:
        yield {
            "Authorization": "Bearer test_token",
            "x-dev-auth-mock": "true",
            "x-dev-auth-roles": "customer",
            "x-dev-auth-user-id": "test-user",
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
