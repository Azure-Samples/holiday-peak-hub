"""Shared compensating transaction framework for saga handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

CompensationCallable = Callable[[], Awaitable[None]]


@dataclass(slots=True)
class CompensationAction:
    """Single compensating action within a saga rollback path."""

    name: str
    execute: CompensationCallable


@dataclass(slots=True)
class CompensationResult:
    """Execution result for compensation actions."""

    completed: list[str] = field(default_factory=list)
    failed_action: str | None = None
    failed_error: Exception | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether all compensation actions completed successfully."""
        return self.failed_error is None


async def execute_compensation(
    actions: list[CompensationAction],
    *,
    continue_on_error: bool = False,
) -> CompensationResult:
    """Execute compensating actions in order with optional continue-on-error behavior."""

    result = CompensationResult()
    for action in actions:
        try:
            await action.execute()
            result.completed.append(action.name)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            result.failed_action = action.name
            result.failed_error = exc
            if not continue_on_error:
                return result
    return result
