"""Agent client for invoking agent REST endpoints with resilience."""

import logging
from typing import Any

import httpx
from circuitbreaker import CircuitBreakerError, circuit
from crud_service.config import get_settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)
settings = get_settings()


class AgentClient:
    """
    Client for invoking agent REST endpoints with timeout and fallback.

    Used for optional agent calls (e.g., enrichment, recommendations).
    If agent is unavailable or times out, fallback to basic logic.
    """

    def __init__(self) -> None:
        self.timeout = httpx.Timeout(settings.agent_timeout_seconds)
        self.enable_fallback = settings.enable_agent_fallback

    def _resolve_agent_url(self, explicit_url: str | None, service_name: str) -> str | None:
        """Resolve target agent URL using explicit override or APIM path convention."""
        if explicit_url:
            return explicit_url.rstrip("/")

        apim_base = settings.agent_apim_base_url
        if not apim_base:
            return None

        return f"{apim_base.rstrip('/')}/agents/{service_name}"

    @circuit(
        failure_threshold=settings.agent_circuit_failure_threshold,
        recovery_timeout=settings.agent_circuit_recovery_seconds,
        expected_exception=httpx.HTTPError,
    )
    @retry(
        stop=stop_after_attempt(settings.agent_retry_attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        reraise=True,
    )
    async def _call_endpoint(self, agent_url: str, endpoint: str, data: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{agent_url}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    async def call_endpoint(
        self,
        agent_url: str | None,
        endpoint: str,
        data: dict[str, Any],
        fallback_value: Any = None,
    ) -> Any:
        """Invoke an agent REST endpoint with timeout and fallback."""
        if not agent_url:
            return fallback_value
        try:
            return await self._call_endpoint(agent_url, endpoint, data)
        except (httpx.TimeoutException, httpx.HTTPError, CircuitBreakerError) as exc:
            logger.warning(
                "Agent call failed; using fallback",
                extra={
                    "agent_url": agent_url,
                    "endpoint": endpoint,
                    "error": str(exc),
                },
            )
            if self.enable_fallback:
                return fallback_value
            raise

    async def get_user_recommendations(
        self, user_id: str, items: list[dict[str, Any]] | None = None
    ) -> dict[str, Any] | None:
        """Get cart recommendations from the cart intelligence agent."""
        payload = {"user_id": user_id, "items": items or []}
        return await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.cart_intelligence_agent_url,
                "ecommerce-cart-intelligence",
            ),
            endpoint="/invoke",
            data=payload,
            fallback_value=None,
        )

    async def get_product_enrichment(self, sku: str) -> dict[str, Any] | None:
        """Get enriched product details from the enrichment agent."""
        if not settings.product_enrichment_agent_url:
            return None

        result = await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.product_enrichment_agent_url,
                "ecommerce-product-detail-enrichment",
            ),
            endpoint="/invoke",
            data={"sku": sku},
            fallback_value=None,
        )
        if not result:
            return None
        if isinstance(result, dict) and "enriched_product" in result:
            return result.get("enriched_product")
        return result

    async def calculate_dynamic_pricing(self, sku: str) -> float | None:
        """Get dynamic pricing from checkout support agent (pricing context)."""
        result = await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.checkout_support_agent_url,
                "ecommerce-checkout-support",
            ),
            endpoint="/invoke",
            data={"items": [{"sku": sku, "quantity": 1}]},
            fallback_value=None,
        )
        if not result or not isinstance(result, dict):
            return None
        pricing = result.get("pricing") or []
        if pricing and isinstance(pricing, list):
            active = pricing[0].get("active") if isinstance(pricing[0], dict) else None
            if isinstance(active, dict):
                return active.get("amount")
        return None

    async def get_inventory_status(self, sku: str) -> dict[str, Any]:
        """Get inventory status from inventory health agent."""
        fallback = {"available": True, "quantity": 999}
        result = await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.inventory_health_agent_url,
                "inventory-health-check",
            ),
            endpoint="/invoke",
            data={"sku": sku},
            fallback_value=fallback,
        )
        if not isinstance(result, dict):
            return fallback
        inventory = result.get("inventory_context") or {}
        item = inventory.get("item") if isinstance(inventory, dict) else None
        if isinstance(item, dict):
            available = item.get("available")
            return {
                "available": available is None or available > 0,
                "quantity": available if available is not None else 0,
                "raw": result,
            }
        return result

    # ── Catalog Search ──────────────────────────────────────────────

    async def semantic_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Semantic product search via the catalog-search agent."""
        result = await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.catalog_search_agent_url,
                "ecommerce-catalog-search",
            ),
            endpoint="/invoke",
            data={"query": query, "limit": limit},
            fallback_value=None,
        )
        if isinstance(result, dict):
            return result.get("products") or result.get("results") or []
        return result if isinstance(result, list) else []

    # ── Order Status ────────────────────────────────────────────────

    async def get_order_status(self, order_id: str) -> dict[str, Any] | None:
        """Get enriched order status with tracking from the order-status agent."""
        return await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.order_status_agent_url,
                "ecommerce-order-status",
            ),
            endpoint="/invoke",
            data={"order_id": order_id},
            fallback_value=None,
        )

    # ── Inventory Reservation ───────────────────────────────────────

    async def validate_reservation(self, sku: str, quantity: int) -> dict[str, Any] | None:
        """Validate stock reservation via the reservation agent."""
        return await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.inventory_reservation_agent_url,
                "inventory-reservation-validation",
            ),
            endpoint="/invoke",
            data={"sku": sku, "request_qty": quantity},
            fallback_value=None,
        )

    # ── Logistics ───────────────────────────────────────────────────

    async def get_delivery_eta(self, tracking_id: str) -> dict[str, Any] | None:
        """Compute delivery ETA from the ETA agent."""
        return await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.logistics_eta_agent_url,
                "logistics-eta-computation",
            ),
            endpoint="/invoke",
            data={"tracking_id": tracking_id},
            fallback_value=None,
        )

    async def get_carrier_recommendation(self, tracking_id: str) -> dict[str, Any] | None:
        """Get optimal carrier recommendation."""
        return await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.logistics_carrier_agent_url,
                "logistics-carrier-selection",
            ),
            endpoint="/invoke",
            data={"tracking_id": tracking_id},
            fallback_value=None,
        )

    async def get_return_plan(self, tracking_id: str) -> dict[str, Any] | None:
        """Generate a returns plan from the returns agent."""
        return await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.logistics_returns_agent_url,
                "logistics-returns-support",
            ),
            endpoint="/invoke",
            data={"tracking_id": tracking_id},
            fallback_value=None,
        )

    # ── CRM ─────────────────────────────────────────────────────────

    async def get_customer_profile(self, contact_id: str) -> dict[str, Any] | None:
        """Get aggregated customer profile from CRM agent."""
        return await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.crm_profile_agent_url,
                "crm-profile-aggregation",
            ),
            endpoint="/invoke",
            data={"contact_id": contact_id},
            fallback_value=None,
        )

    async def get_personalization(self, contact_id: str) -> dict[str, Any] | None:
        """Get personalization recommendations from the segmentation agent."""
        return await self.call_endpoint(
            agent_url=self._resolve_agent_url(
                settings.crm_segmentation_agent_url,
                "crm-segmentation-personalization",
            ),
            endpoint="/invoke",
            data={"contact_id": contact_id},
            fallback_value=None,
        )


# Global instance
_agent_client: AgentClient | None = None


def get_agent_client() -> AgentClient:
    """Get global agent client instance."""
    global _agent_client
    if _agent_client is None:
        _agent_client = AgentClient()
    return _agent_client
