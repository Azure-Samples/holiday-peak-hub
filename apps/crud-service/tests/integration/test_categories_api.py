"""Integration tests for category API robustness."""

from unittest.mock import AsyncMock, patch

from crud_service.main import app
from fastapi.testclient import TestClient

_SAMPLE_CATEGORY = {
    "id": "cat-1",
    "name": "Electronics",
    "description": "Devices and accessories",
}

def test_list_categories_anonymous_returns_data():
    """List categories should return valid rows."""
    with patch(
        "crud_service.routes.categories.category_repo.query",
        new_callable=AsyncMock,
        return_value=[_SAMPLE_CATEGORY],
    ):
        with TestClient(app) as client:
            response = client.get("/api/categories")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == _SAMPLE_CATEGORY["id"]


def test_list_categories_skips_malformed_records():
    """Malformed category rows should be filtered out instead of crashing."""
    malformed_category = {
        "id": "cat-bad",
        "description": "Missing required name",
    }

    with patch(
        "crud_service.routes.categories.category_repo.query",
        new_callable=AsyncMock,
        return_value=[malformed_category, _SAMPLE_CATEGORY],
    ):
        with TestClient(app) as client:
            response = client.get("/api/categories")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == _SAMPLE_CATEGORY["id"]


def test_list_categories_repo_failure_returns_503():
    """Repository/runtime failures should return 503 for category list endpoint."""
    with patch(
        "crud_service.routes.categories.category_repo.query",
        new_callable=AsyncMock,
        side_effect=RuntimeError("transient db failure"),
    ):
        with TestClient(app) as client:
            response = client.get("/api/categories")

    assert response.status_code == 503
    assert response.json()["detail"] == "Categories are temporarily unavailable"


def test_list_categories_none_repo_result_returns_503():
    """None category list output should degrade to stable 503."""
    with patch(
        "crud_service.routes.categories.category_repo.query",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with TestClient(app) as client:
            response = client.get("/api/categories")

    assert response.status_code == 503
    assert response.json()["detail"] == "Categories are temporarily unavailable"


def test_list_categories_non_iterable_repo_result_returns_503():
    """Non-iterable category list output should degrade to stable 503."""
    with patch(
        "crud_service.routes.categories.category_repo.query",
        new_callable=AsyncMock,
        return_value=42,
    ):
        with TestClient(app) as client:
            response = client.get("/api/categories")

    assert response.status_code == 503
    assert response.json()["detail"] == "Categories are temporarily unavailable"
