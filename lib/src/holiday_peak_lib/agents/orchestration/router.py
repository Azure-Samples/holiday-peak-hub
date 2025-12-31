"""Routing logic for tool/model selection with logging."""
from typing import Any, Callable, Dict

from holiday_peak_lib.utils.logging import configure_logging, log_async_operation


logger = configure_logging()


class RoutingStrategy:
    """Simple routing registry mapping intents to handlers."""

    def __init__(self) -> None:
        self._routes: Dict[str, Callable[..., Any]] = {}

    def register(self, intent: str, handler: Callable[..., Any]) -> None:
        self._routes[intent] = handler
        logger.info("op=router.register intent=%s status=success", intent)

    async def route(self, intent: str, payload: Dict[str, Any]) -> Any:
        handler = self._routes.get(intent)
        if not handler:
            raise KeyError(f"No handler for intent {intent}")
        return await log_async_operation(
            logger,
            name="router.route",
            intent=intent,
            func=lambda: handler(payload),
            token_count=None,
            metadata={"payload_size": len(str(payload))},
        )
