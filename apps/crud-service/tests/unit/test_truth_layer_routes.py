"""Unit tests for truth-layer route modules."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from crud_service.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# truth_attributes
# ---------------------------------------------------------------------------


class TestTruthAttributesRoutes:
    """Tests for GET /api/truth/attributes/{entity_id}[/{field_name}]."""

    def test_get_truth_attributes_returns_list(self, client):
        attrs = [
            {
                "id": "attr-1",
                "entity_id": "prod-1",
                "field_name": "color",
                "value": "red",
                "source_model": "gpt-4",
                "confidence": 0.98,
                "approved_at": "2024-01-01T00:00:00Z",
                "approved_by": "admin",
            }
        ]
        with patch(
            "crud_service.routes.truth_attributes.truth_attr_repo.query",
            new=AsyncMock(return_value=attrs),
        ):
            resp = client.get("/api/truth/attributes/prod-1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["field_name"] == "color"

    def test_get_truth_attributes_empty(self, client):
        with patch(
            "crud_service.routes.truth_attributes.truth_attr_repo.query",
            new=AsyncMock(return_value=[]),
        ):
            resp = client.get("/api/truth/attributes/unknown-entity")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_single_truth_attribute(self, client):
        attrs = [
            {
                "id": "attr-1",
                "entity_id": "prod-1",
                "field_name": "color",
                "value": "blue",
            }
        ]
        with patch(
            "crud_service.routes.truth_attributes.truth_attr_repo.query",
            new=AsyncMock(return_value=attrs),
        ):
            resp = client.get("/api/truth/attributes/prod-1/color")
        assert resp.status_code == 200
        assert resp.json()["field_name"] == "color"

    def test_get_single_truth_attribute_not_found(self, client):
        with patch(
            "crud_service.routes.truth_attributes.truth_attr_repo.query",
            new=AsyncMock(return_value=[]),
        ):
            resp = client.get("/api/truth/attributes/prod-1/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# proposed_attributes
# ---------------------------------------------------------------------------


class TestProposedAttributesRoutes:
    """Tests for GET /api/proposed/attributes/{entity_id}."""

    def test_list_proposed_attributes(self, client):
        items = [
            {
                "id": "pa-1",
                "entity_id": "prod-2",
                "field_name": "material",
                "proposed_value": "cotton",
                "status": "pending",
                "confidence": 0.85,
            }
        ]
        with patch(
            "crud_service.routes.proposed_attributes.proposed_attr_repo.query",
            new=AsyncMock(return_value=items),
        ):
            resp = client.get("/api/proposed/attributes/prod-2")
        assert resp.status_code == 200
        assert resp.json()[0]["status"] == "pending"

    def test_filter_proposed_attributes_by_status(self, client):
        items = [
            {
                "id": "pa-1",
                "entity_id": "prod-2",
                "field_name": "x",
                "proposed_value": 1,
                "status": "pending",
            },
            {
                "id": "pa-2",
                "entity_id": "prod-2",
                "field_name": "y",
                "proposed_value": 2,
                "status": "approved",
            },
        ]
        with patch(
            "crud_service.routes.proposed_attributes.proposed_attr_repo.query",
            new=AsyncMock(return_value=items),
        ):
            resp = client.get("/api/proposed/attributes/prod-2?status=pending")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"

    def test_get_single_proposed_attribute_not_found(self, client):
        with patch(
            "crud_service.routes.proposed_attributes.proposed_attr_repo.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            resp = client.get("/api/proposed/attributes/prod-2/missing-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# schemas_registry
# ---------------------------------------------------------------------------


class TestSchemasRegistryRoutes:
    """Tests for /api/schemas endpoints."""

    def test_list_schemas(self, client):
        items = [
            {
                "id": "cat-1",
                "category_id": "cat-1",
                "category_name": "Apparel",
                "fields": [],
            }
        ]
        with patch(
            "crud_service.routes.schemas_registry.schema_repo.query",
            new=AsyncMock(return_value=items),
        ):
            resp = client.get("/api/schemas")
        assert resp.status_code == 200
        assert resp.json()[0]["category_id"] == "cat-1"

    def test_get_schema_by_category(self, client):
        items = [
            {"id": "cat-2", "category_id": "cat-2", "category_name": "Electronics", "fields": []}
        ]
        with patch(
            "crud_service.routes.schemas_registry.schema_repo.query",
            new=AsyncMock(return_value=items),
        ):
            resp = client.get("/api/schemas/cat-2")
        assert resp.status_code == 200
        assert resp.json()["category_name"] == "Electronics"

    def test_get_schema_not_found(self, client):
        with patch(
            "crud_service.routes.schemas_registry.schema_repo.query",
            new=AsyncMock(return_value=[]),
        ):
            resp = client.get("/api/schemas/no-cat")
        assert resp.status_code == 404

    def test_create_schema(self, client):
        new_schema = {
            "id": "cat-3",
            "category_id": "cat-3",
            "category_name": "Toys",
            "version": "1.0",
            "fields": [],
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
        }
        with (
            patch(
                "crud_service.routes.schemas_registry.schema_repo.query",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "crud_service.routes.schemas_registry.schema_repo.create",
                new=AsyncMock(return_value=new_schema),
            ),
        ):
            resp = client.post(
                "/api/schemas",
                json={
                    "category_id": "cat-3",
                    "category_name": "Toys",
                    "version": "1.0",
                    "fields": [],
                },
            )
        assert resp.status_code == 201
        assert resp.json()["category_id"] == "cat-3"


# ---------------------------------------------------------------------------
# completeness
# ---------------------------------------------------------------------------


class TestCompletenessRoutes:
    """Tests for /api/completeness endpoints."""

    def test_get_completeness_report(self, client):
        report = {
            "id": "cr-1",
            "entity_id": "prod-3",
            "score": 0.8,
            "required_fields": 10,
            "completed_fields": 8,
            "gaps": [],
        }
        with patch(
            "crud_service.routes.completeness.completeness_repo.query",
            new=AsyncMock(return_value=[report]),
        ):
            resp = client.get("/api/completeness/prod-3")
        assert resp.status_code == 200
        assert resp.json()["score"] == 0.8

    def test_get_completeness_not_found(self, client):
        with patch(
            "crud_service.routes.completeness.completeness_repo.query",
            new=AsyncMock(return_value=[]),
        ):
            resp = client.get("/api/completeness/no-product")
        assert resp.status_code == 404

    def test_get_completeness_summary(self, client):
        reports = [
            {
                "id": "r1",
                "entity_id": "p1",
                "score": 1.0,
                "required_fields": 5,
                "completed_fields": 5,
                "gaps": [],
            },
            {
                "id": "r2",
                "entity_id": "p2",
                "score": 0.8,
                "required_fields": 5,
                "completed_fields": 4,
                "gaps": [],
            },
            {
                "id": "r3",
                "entity_id": "p3",
                "score": 0.5,
                "required_fields": 5,
                "completed_fields": 2,
                "gaps": [],
            },
        ]
        with patch(
            "crud_service.routes.completeness.completeness_repo.query",
            new=AsyncMock(return_value=reports),
        ):
            resp = client.get("/api/completeness/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_products"] == 3
        assert data["fully_complete"] == 1
        assert data["needs_enrichment"] == 1
        assert data["critical_gaps"] == 1

    def test_get_completeness_summary_empty(self, client):
        with patch(
            "crud_service.routes.completeness.completeness_repo.query",
            new=AsyncMock(return_value=[]),
        ):
            resp = client.get("/api/completeness/summary")
        assert resp.status_code == 200
        assert resp.json()["total_products"] == 0

    def test_truth_analytics_summary_shape_and_calculations(self, client):
        completeness_items = [
            {
                "id": "c-1",
                "entity_id": "p-1",
                "category_id": "cat-a",
                "score": 0.80,
                "generated_at": "2026-03-24T10:00:00Z",
            },
            {
                "id": "c-2",
                "entity_id": "p-2",
                "category_id": "cat-b",
                "score": 0.60,
                "generated_at": "2026-03-24T11:00:00Z",
            },
        ]
        proposals = [
            {
                "id": "pa-1",
                "status": "pending",
                "proposed_at": "2026-03-24T10:00:00Z",
            },
            {
                "id": "pa-2",
                "status": "approved",
                "reviewed_by": "system",
                "proposed_at": "2026-03-24T10:00:00Z",
                "reviewed_at": "2026-03-24T10:10:00Z",
            },
            {
                "id": "pa-3",
                "status": "rejected",
                "proposed_at": "2026-03-24T10:00:00Z",
                "reviewed_at": "2026-03-24T10:20:00Z",
            },
        ]
        audit_events = [
            {"id": "a-1", "action": "enrichment_completed", "timestamp": "2026-03-24T10:05:00Z"},
            {"id": "a-2", "action": "acp_export", "metadata": {"target": "acp"}},
            {"id": "a-3", "action": "ucp_export", "metadata": {"target": "ucp"}},
        ]

        with (
            patch(
                "crud_service.routes.completeness.completeness_repo.query",
                new=AsyncMock(return_value=completeness_items),
            ),
            patch(
                "crud_service.routes.completeness.proposed_attr_repo.query",
                new=AsyncMock(return_value=proposals),
            ),
            patch(
                "crud_service.routes.completeness.audit_repo.query",
                new=AsyncMock(return_value=audit_events),
            ),
        ):
            resp = client.get("/api/truth/analytics/summary")

        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {
            "overall_completeness",
            "total_products",
            "enrichment_jobs_processed",
            "auto_approved",
            "sent_to_hitl",
            "queue_pending",
            "queue_approved",
            "queue_rejected",
            "avg_review_time_minutes",
            "acp_exports",
            "ucp_exports",
        }
        assert data["total_products"] == 2
        assert data["overall_completeness"] == pytest.approx(0.7)
        assert data["queue_pending"] == 1
        assert data["queue_approved"] == 1
        assert data["queue_rejected"] == 1
        assert data["sent_to_hitl"] == 3
        assert data["auto_approved"] == 1
        assert data["enrichment_jobs_processed"] == 1
        assert data["avg_review_time_minutes"] == pytest.approx(15.0)
        assert data["acp_exports"] == 1
        assert data["ucp_exports"] == 1

    def test_truth_analytics_completeness_returns_category_rows(self, client):
        completeness_items = [
            {"id": "c-1", "entity_id": "p-1", "category_id": "cat-a", "score": 1.0},
            {"id": "c-2", "entity_id": "p-2", "category_id": "cat-a", "score": 0.5},
            {"id": "c-3", "entity_id": "p-3", "category_id": "cat-b", "score": 0.75},
        ]
        with patch(
            "crud_service.routes.completeness.completeness_repo.query",
            new=AsyncMock(return_value=completeness_items),
        ):
            resp = client.get("/api/truth/analytics/completeness")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        cat_a = next(row for row in data if row["category"] == "cat-a")
        cat_b = next(row for row in data if row["category"] == "cat-b")
        assert cat_a["product_count"] == 2
        assert cat_a["completeness"] == pytest.approx(0.75)
        assert cat_b["product_count"] == 1
        assert cat_b["completeness"] == pytest.approx(0.75)

    def test_truth_analytics_throughput_returns_time_series(self, client):
        now = datetime.now(UTC)
        minute = timedelta(minutes=1)
        completeness_items = [
            {"id": "c-1", "generated_at": (now - minute * 35).isoformat()},
            {"id": "c-2", "generated_at": (now - minute * 5).isoformat()},
        ]
        proposal_items = [
            {"id": "p-1", "status": "approved", "reviewed_at": (now - minute * 34).isoformat()},
            {"id": "p-2", "status": "rejected", "reviewed_at": (now - minute * 4).isoformat()},
        ]
        audit_items = [
            {"id": "a-1", "action": "enrichment_completed", "timestamp": (now - minute * 33).isoformat()},
            {"id": "a-2", "action": "enrichment_completed", "timestamp": (now - minute * 3).isoformat()},
        ]

        with (
            patch(
                "crud_service.routes.completeness.completeness_repo.query",
                new=AsyncMock(return_value=completeness_items),
            ),
            patch(
                "crud_service.routes.completeness.proposed_attr_repo.query",
                new=AsyncMock(return_value=proposal_items),
            ),
            patch(
                "crud_service.routes.completeness.audit_repo.query",
                new=AsyncMock(return_value=audit_items),
            ),
        ):
            resp = client.get("/api/truth/analytics/throughput?window_hours=1&interval_minutes=30")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        assert all(
            set(point.keys()) == {"timestamp", "ingested", "enriched", "approved", "rejected"}
            for point in data
        )
        assert sum(point["ingested"] for point in data) == 2
        assert sum(point["enriched"] for point in data) == 2
        assert sum(point["approved"] for point in data) == 1
        assert sum(point["rejected"] for point in data) == 1


# ---------------------------------------------------------------------------
# audit_trail
# ---------------------------------------------------------------------------


class TestAuditTrailRoutes:
    """Tests for /api/audit endpoints."""

    def test_get_audit_trail_for_entity(self, client):
        events = [
            {
                "id": "evt-1",
                "entity_id": "prod-4",
                "action": "enrichment",
                "actor": "system",
                "timestamp": "2024-01-01T00:00:00Z",
            }
        ]
        with patch(
            "crud_service.routes.audit_trail.audit_repo.query",
            new=AsyncMock(return_value=events),
        ):
            resp = client.get("/api/audit/prod-4")
        assert resp.status_code == 200
        assert resp.json()[0]["action"] == "enrichment"

    def test_get_audit_trail_with_action_filter(self, client):
        events = [
            {"id": "e1", "entity_id": "prod-4", "action": "enrichment", "actor": "system"},
            {"id": "e2", "entity_id": "prod-4", "action": "approval", "actor": "user-1"},
        ]
        with patch(
            "crud_service.routes.audit_trail.audit_repo.query",
            new=AsyncMock(return_value=events),
        ):
            resp = client.get("/api/audit/prod-4?action=approval")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["action"] == "approval"

    def test_query_audit_events(self, client):
        events = [
            {"id": "e1", "entity_id": "p1", "action": "enrichment", "actor": "system"},
            {"id": "e2", "entity_id": "p2", "action": "enrichment", "actor": "user-1"},
        ]
        with patch(
            "crud_service.routes.audit_trail.audit_repo.query",
            new=AsyncMock(return_value=events),
        ):
            resp = client.get("/api/audit?action=enrichment&actor=system")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["actor"] == "system"


# ---------------------------------------------------------------------------
# ucp_products
# ---------------------------------------------------------------------------


class TestUCPProductsRoutes:
    """Tests for /api/ucp/products endpoints."""

    def test_list_ucp_products(self, client):
        products = [
            {
                "id": "prod-5",
                "sku": "SKU-001",
                "name": "Test Product",
                "category_id": "cat-1",
                "attributes": {"color": "red"},
            }
        ]
        with patch(
            "crud_service.routes.ucp_products.truth_product_repo.query",
            new=AsyncMock(return_value=products),
        ):
            resp = client.get("/api/ucp/products")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["entity_id"] == "prod-5"
        assert data[0]["attributes"][0]["name"] == "color"

    def test_list_ucp_products_with_category_filter(self, client):
        products = [{"id": "prod-6", "category_id": "cat-2", "attributes": {}}]
        with patch(
            "crud_service.routes.ucp_products.truth_product_repo.query",
            new=AsyncMock(return_value=products),
        ):
            resp = client.get("/api/ucp/products?category=cat-2")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_ucp_product(self, client):
        product = {"id": "prod-7", "name": "Widget", "attributes": {"size": "L"}}
        with patch(
            "crud_service.routes.ucp_products.truth_product_repo.get_by_id",
            new=AsyncMock(return_value=product),
        ):
            resp = client.get("/api/ucp/products/prod-7")
        assert resp.status_code == 200
        assert resp.json()["entity_id"] == "prod-7"

    def test_get_ucp_product_not_found(self, client):
        with patch(
            "crud_service.routes.ucp_products.truth_product_repo.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            resp = client.get("/api/ucp/products/missing")
        assert resp.status_code == 404
