"""Routing logic for intent handling with optional SLM-first escalation."""

import inspect
from typing import Any, Callable

from holiday_peak_lib.agents.complexity import assess_complexity
from holiday_peak_lib.utils.logging import configure_logging, log_async_operation

logger = configure_logging()


class RoutingStrategy:
    """Routing registry with SLM-first intent execution support.

    Handlers can be registered as single intent handlers via ``register``
    (backward-compatible) or as explicit model-tier handlers via
    ``register_model_handlers``.

    Tiered execution rules:
    1. Run SLM handler first when available.
    2. Escalate to LLM when complexity is above threshold.
    3. Escalate to LLM when SLM explicitly requests upgrade.
    """

    def __init__(self, complexity_threshold: float = 0.5) -> None:
        self._routes: dict[str, dict[str, Callable[..., Any]]] = {}
        self._complexity_threshold = complexity_threshold

    def _assess_complexity(self, payload: dict[str, Any]) -> float:
        """Delegate to shared complexity heuristic."""
        return assess_complexity(payload)

    def _extract_result_text(self, result: Any) -> str:
        """Best-effort extraction of textual response for upgrade checks."""

        if isinstance(result, dict):
            return str(
                result.get("response") or result.get("content") or result.get("message") or result
            )
        return str(result)

    def _should_upgrade_from_slm(self, payload: dict[str, Any], slm_result: Any) -> bool:
        """Determine whether to escalate from SLM to LLM."""

        if self._assess_complexity(payload) >= self._complexity_threshold:
            return True
        return self._extract_result_text(slm_result).strip().lower() == "upgrade"

    async def _invoke_handler(self, handler: Callable[..., Any], payload: dict[str, Any]) -> Any:
        """Invoke sync or async handlers uniformly."""

        result = handler(payload)
        if inspect.isawaitable(result):
            return await result
        return result

    def register(self, intent: str, handler: Callable[..., Any]) -> None:
        self._routes[intent] = {"default": handler}
        logger.info("op=router.register intent=%s status=success", intent)

    def register_model_handlers(
        self,
        intent: str,
        *,
        slm_handler: Callable[..., Any],
        llm_handler: Callable[..., Any] | None = None,
    ) -> None:
        """Register SLM/LLM handlers for an intent."""

        routes: dict[str, Callable[..., Any]] = {"slm": slm_handler}
        if llm_handler is not None:
            routes["llm"] = llm_handler
        self._routes[intent] = routes
        logger.info(
            "op=router.register_models intent=%s has_llm=%s status=success",
            intent,
            llm_handler is not None,
        )

    async def route(self, intent: str, payload: dict[str, Any]) -> Any:
        handlers = self._routes.get(intent)
        if not handlers:
            raise KeyError(f"No handler for intent {intent}")

        default_handler = handlers.get("default")
        slm_handler = handlers.get("slm")
        llm_handler = handlers.get("llm")

        if default_handler is not None:
            selected_name = "default"

            async def _run() -> Any:
                return await self._invoke_handler(default_handler, payload)

        elif slm_handler is not None:
            selected_name = "slm"

            async def _run() -> Any:
                slm_result = await self._invoke_handler(slm_handler, payload)
                if llm_handler is not None and self._should_upgrade_from_slm(payload, slm_result):
                    return await self._invoke_handler(llm_handler, payload)
                return slm_result

        else:
            raise KeyError(f"No handler for intent {intent}")

        return await log_async_operation(
            logger,
            name="router.route",
            intent=intent,
            func=_run,
            token_count=None,
            metadata={
                "payload_size": len(str(payload)),
                "selected_handler": selected_name,
            },
        )
