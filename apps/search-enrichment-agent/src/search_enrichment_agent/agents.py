"""Search enrichment agent implementation and MCP tool registration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx
from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.evaluation import confidence_calibration_bins, run_evaluation
from holiday_peak_lib.mcp.ai_search_indexing import (
    AISearchIndexingClient,
    build_ai_search_indexing_client_from_env,
    register_ai_search_indexing_tools,
)
from holiday_peak_lib.schemas.truth import SearchEnrichedProduct, SourceType
from holiday_peak_lib.utils.telemetry import get_foundry_tracer

from .adapters import SearchEnrichmentAdapters, build_search_enrichment_adapters
from .enrichment_engine import SearchEnrichmentEngine

_API_LIVENESS_DECISION = "liveness.api.invoke"


@dataclass
class SearchEnrichmentOrchestrator:
    """Template-style orchestration for MCP and event-triggered enrichment."""

    adapters: SearchEnrichmentAdapters
    engine: SearchEnrichmentEngine

    async def run(
        self,
        *,
        entity_id: str,
        has_model_backend: bool,
        trigger: str,
    ) -> dict[str, Any]:
        approved = await self.adapters.approved_truth.get_approved_data(entity_id)
        if approved is None:
            return {
                "service": "search-enrichment-agent",
                "entity_id": entity_id,
                "status": "not_found",
                "message": "approved truth data not found",
                "trigger": trigger,
            }

        strategy = "simple"
        simple_fields = self.engine.build_simple_fields(approved)
        enriched_fields = simple_fields
        degradation = False

        if has_model_backend and self.engine.is_complex(approved):
            model_fields = await self.adapters.foundry.enrich_complex_fields(
                entity_id=entity_id,
                approved_truth=approved,
            )
            if model_fields.get("_status") == "ok":
                strategy = "complex"
                enriched_fields = self.engine.build_complex_fields(approved, model_fields)
            else:
                strategy = "simple"
                degradation = True

        validated_fields = self.engine.validate_fields(enriched_fields)
        enriched_product = SearchEnrichedProduct(
            sku=entity_id,
            score=1.0 if strategy == "complex" else 0.75,
            sourceType=(
                SourceType.AI_REASONING if strategy == "complex" else SourceType.PRODUCT_CONTEXT
            ),
            sourceAssets=[],
            originalData=approved,
            enrichedData=validated_fields,
            intentClassification=None,
            reasoning=(
                "Complex strategy using model-assisted enrichment"
                if strategy == "complex"
                else "Simple deterministic strategy from approved truth"
            ),
        )

        stored = await self.adapters.enriched_store.upsert(enriched_product)
        indexing = await self._run_indexing_after_upsert(entity_id, enriched_product)

        return {
            "service": "search-enrichment-agent",
            "entity_id": entity_id,
            "status": "enriched",
            "strategy": strategy,
            "graceful_degradation": degradation,
            "trigger": trigger,
            "container": "search_enriched_products",
            "enriched": enriched_product.model_dump(mode="json", by_alias=True),
            "stored": stored,
            "indexing": indexing,
        }

    async def _run_indexing_after_upsert(
        self,
        entity_id: str,
        enriched_product: SearchEnrichedProduct,
    ) -> dict[str, Any]:
        search_indexing = self.adapters.search_indexing
        if search_indexing is None:
            return {
                "status": "skipped",
                "reason": "ai_search_not_configured",
            }
        try:
            return await search_indexing.sync_after_upsert(
                entity_id=entity_id,
                enriched=enriched_product,
            )
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            return {
                "status": "error",
                "operation": "post_upsert_indexing",
                "error": {
                    "kind": "runtime",
                    "message": str(exc),
                },
            }


def _extract_entity_id(payload: dict[str, Any]) -> str | None:
    entity_id = payload.get("entity_id") or payload.get("product_id") or payload.get("sku")
    if entity_id is None:
        return None
    return str(entity_id)


def _resolve_liveness_status(result: dict[str, Any], *, default: str) -> str:
    status = result.get("status")
    if status is not None:
        resolved = str(status).strip()
        if resolved:
            return resolved
    if result.get("error") is not None:
        return "error"
    return default


def _build_liveness_metadata(
    *,
    surface: str,
    trigger: str,
    endpoint: str | None = None,
    eventhub: str | None = None,
    entity_id: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "surface": surface,
        "trigger": trigger,
    }
    if endpoint:
        metadata["endpoint"] = endpoint
    if eventhub:
        metadata["eventhub"] = eventhub
    if entity_id:
        metadata["entity_id"] = entity_id
    if status:
        metadata["status"] = status
    return metadata


def _with_mcp_liveness(
    agent: BaseRetailAgent,
    *,
    tool_name: str,
    handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    """Decorator-style wrapper that emits MCP liveness traces for tool handlers."""

    async def wrapped(payload: dict[str, Any]) -> dict[str, Any]:
        entity_id = _extract_entity_id(payload)
        try:
            result = await handler(payload)
        except Exception:
            get_foundry_tracer(agent.service_name or type(agent).__name__).trace_tool_call(
                tool_name=tool_name,
                outcome="error",
                metadata=_build_liveness_metadata(
                    surface="mcp",
                    trigger="mcp",
                    endpoint=tool_name,
                    entity_id=entity_id,
                    status="error",
                ),
            )
            raise

        status = _resolve_liveness_status(result, default="unknown")
        outcome = "missing_entity_id" if entity_id is None else status
        get_foundry_tracer(agent.service_name or type(agent).__name__).trace_tool_call(
            tool_name=tool_name,
            outcome=outcome,
            metadata=_build_liveness_metadata(
                surface="mcp",
                trigger="mcp",
                endpoint=tool_name,
                entity_id=entity_id,
                status=status,
            ),
        )
        return result

    return wrapped


class SearchEnrichmentAgent(BaseRetailAgent):
    """Agent producing search-optimized enrichment fields from approved truth data."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_search_enrichment_adapters()
        self._adapters.foundry.set_model_invoker(self.invoke_model)
        self._engine = SearchEnrichmentEngine()
        self._orchestrator = SearchEnrichmentOrchestrator(
            adapters=self._adapters,
            engine=self._engine,
        )

    @property
    def adapters(self) -> SearchEnrichmentAdapters:
        return self._adapters

    @property
    def engine(self) -> SearchEnrichmentEngine:
        return self._engine

    def _trace_api_liveness(
        self,
        *,
        outcome: str,
        entity_id: str | None = None,
        status: str | None = None,
    ) -> None:
        self._trace_decision(
            decision=_API_LIVENESS_DECISION,
            outcome=outcome,
            metadata=_build_liveness_metadata(
                surface="api",
                trigger="invoke",
                endpoint="/invoke",
                entity_id=entity_id,
                status=status,
            ),
        )

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        entity_id = request.get("entity_id") or request.get("product_id") or request.get("sku")
        if not entity_id:
            self._trace_decision(
                decision="search_enrichment_validation",
                outcome="missing_entity_id",
                metadata={"service": self.service_name},
            )
            self._trace_api_liveness(outcome="missing_entity_id", status="error")
            return {"error": "entity_id is required"}

        resolved_entity_id = str(entity_id)
        try:
            result = await self._orchestrator.run(
                entity_id=resolved_entity_id,
                has_model_backend=bool(self.slm or self.llm),
                trigger="invoke",
            )
            liveness_status = _resolve_liveness_status(result, default="unknown")
            self._trace_api_liveness(
                outcome=liveness_status,
                entity_id=resolved_entity_id,
                status=liveness_status,
            )
            self._trace_decision(
                decision="search_enrichment_strategy",
                outcome=str(result.get("strategy", "unknown")),
                metadata={
                    "entity_id": resolved_entity_id,
                    "status": str(result.get("status", "unknown")),
                    "reasoning": str(
                        ((result.get("enriched") or {}).get("reasoning"))
                        if isinstance(result.get("enriched"), dict)
                        else ""
                    ),
                },
            )
            _record_search_enrichment_evaluation(self, entity_id=resolved_entity_id, result=result)
            return result
        except Exception:
            self._trace_api_liveness(
                outcome="error",
                entity_id=resolved_entity_id,
                status="error",
            )
            raise

    async def enrich(self, entity_id: str, *, trigger: str) -> dict[str, Any]:
        return await self._orchestrator.run(
            entity_id=entity_id,
            has_model_backend=bool(self.slm or self.llm),
            trigger=trigger,
        )


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for search enrichment flows."""

    async def enrich(payload: dict[str, Any]) -> dict[str, Any]:
        entity_id = _extract_entity_id(payload)
        if entity_id is None:
            return {"error": "entity_id is required"}

        run_fn: Callable[..., Any] | None = getattr(agent, "enrich", None)
        if callable(run_fn):
            return await run_fn(entity_id, trigger="mcp")

        return await agent.handle({"entity_id": entity_id})

    async def status(payload: dict[str, Any]) -> dict[str, Any]:
        entity_id = _extract_entity_id(payload)
        if entity_id is None:
            return {"error": "entity_id is required"}

        adapters: SearchEnrichmentAdapters = getattr(
            agent,
            "adapters",
            build_search_enrichment_adapters(),
        )
        result = await adapters.enriched_store.get_status(entity_id)
        return result

    mcp.add_tool(
        "/search-enrichment/enrich",
        _with_mcp_liveness(
            agent,
            tool_name="/search-enrichment/enrich",
            handler=enrich,
        ),
    )
    mcp.add_tool(
        "/search-enrichment/status",
        _with_mcp_liveness(
            agent,
            tool_name="/search-enrichment/status",
            handler=status,
        ),
    )
    _register_ai_search_tools(mcp)
    _register_crud_tools(mcp)


def _register_crud_tools(mcp: FastAPIMCPServer) -> None:
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def _register_ai_search_tools(mcp: FastAPIMCPServer) -> None:
    client: AISearchIndexingClient | None = build_ai_search_indexing_client_from_env()
    if client is None:
        return
    register_ai_search_indexing_tools(mcp, client=client)


def _record_search_enrichment_evaluation(
    agent: BaseRetailAgent,
    *,
    entity_id: str,
    result: dict[str, Any],
) -> None:
    enriched = result.get("enriched") if isinstance(result.get("enriched"), dict) else {}
    confidence = float(enriched.get("score", 0.0))
    status = str(result.get("status", "unknown"))
    strategy = str(result.get("strategy", "unknown"))
    calibration = confidence_calibration_bins([(confidence, status == "enriched")], bins=5)

    def _evaluator(_dataset: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "entity_id": entity_id,
            "status_enriched": 1.0 if status == "enriched" else 0.0,
            "confidence": confidence,
            "graceful_degradation": 1.0 if bool(result.get("graceful_degradation")) else 0.0,
            "calibration_gap": float(
                sum(abs(bin_row["avg_confidence"] - bin_row["accuracy"]) for bin_row in calibration)
            ),
            "strategy_simple": 1.0 if strategy == "simple" else 0.0,
            "strategy_complex": 1.0 if strategy == "complex" else 0.0,
        }

    run = run_evaluation(
        dataset=[{"entity_id": entity_id, "status": status, "strategy": strategy}],
        evaluator=_evaluator,
        run_name="search-enrichment-agent",
    )
    agent._get_foundry_tracer().record_evaluation(  # pylint: disable=protected-access
        {
            "domain": "search_enrichment",
            "backend": run.backend,
            "status": run.status,
            "metrics": run.metrics,
            "details": run.details,
        }
    )
