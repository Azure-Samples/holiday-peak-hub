"""Tests for shared compensation framework."""

import pytest
from holiday_peak_lib.utils import CompensationAction, execute_compensation


@pytest.mark.asyncio
async def test_execute_compensation_runs_actions_in_order() -> None:
    completed: list[str] = []

    async def first() -> None:
        completed.append("first")

    async def second() -> None:
        completed.append("second")

    result = await execute_compensation(
        [
            CompensationAction(name="first", execute=first),
            CompensationAction(name="second", execute=second),
        ]
    )

    assert result.succeeded
    assert result.completed == ["first", "second"]
    assert completed == ["first", "second"]


@pytest.mark.asyncio
async def test_execute_compensation_stops_on_first_failure_by_default() -> None:
    completed: list[str] = []

    async def first() -> None:
        completed.append("first")

    async def failing() -> None:
        raise RuntimeError("rollback failed")

    async def after_failure() -> None:
        completed.append("after_failure")

    result = await execute_compensation(
        [
            CompensationAction(name="first", execute=first),
            CompensationAction(name="failing", execute=failing),
            CompensationAction(name="after_failure", execute=after_failure),
        ]
    )

    assert not result.succeeded
    assert result.completed == ["first"]
    assert result.failed_action == "failing"
    assert isinstance(result.failed_error, RuntimeError)
    assert completed == ["first"]
