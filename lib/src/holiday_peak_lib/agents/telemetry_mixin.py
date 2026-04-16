"""Agent telemetry mixin for tracing decisions, tool calls, and model invocations."""

from typing import Any

from holiday_peak_lib.utils.telemetry import get_foundry_tracer


class AgentTelemetryMixin:
    """Mixin providing telemetry tracing for agent operations.

    Expects the host class to expose a ``service_name`` property (str | None).
    """

    service_name: str | None

    def _get_foundry_tracer(self) -> Any:
        service = self.service_name or type(self).__name__
        return get_foundry_tracer(service)

    def _trace_decision(
        self,
        decision: str,
        outcome: str,
        metadata: dict[str, Any],
    ) -> None:
        """Record a routing/selection decision via the Foundry tracer."""
        try:
            self._get_foundry_tracer().trace_decision(
                decision=decision,
                outcome=outcome,
                metadata=metadata,
            )
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return

    def _trace_tools(
        self,
        payload_tools: Any,
        outcome: str,
        metadata: dict[str, Any],
    ) -> None:
        """Record tool participation in a model invocation."""
        tool_names: list[str] = []
        if isinstance(payload_tools, dict):
            tool_names = [str(name) for name in payload_tools]
        elif isinstance(payload_tools, (list, tuple, set)):
            tool_names = [str(name) for name in payload_tools]
        elif payload_tools is not None:
            tool_names = [str(payload_tools)]

        if not tool_names:
            return

        tracer = self._get_foundry_tracer()
        for tool_name in tool_names:
            try:
                tracer.trace_tool_call(
                    tool_name=tool_name,
                    outcome=outcome,
                    metadata=metadata,
                )
            except (AttributeError, TypeError, ValueError, RuntimeError):
                continue
