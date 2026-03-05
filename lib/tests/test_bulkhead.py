"""Unit tests for the async bulkhead."""

import asyncio

import pytest
from holiday_peak_lib.utils.bulkhead import Bulkhead, BulkheadFullError


@pytest.mark.asyncio
class TestBulkhead:
    """Tests for Bulkhead."""

    async def test_successful_call(self):
        bh = Bulkhead("test", concurrency_limit=2, queue_timeout=None)

        async def task():
            return "done"

        result = await bh.call(task)
        assert result == "done"

    async def test_concurrency_limit_enforced(self):
        bh = Bulkhead("test", concurrency_limit=2, queue_timeout=0.0)

        # Hold two slots
        barrier = asyncio.Event()
        release = asyncio.Event()

        async def slow_task():
            release.set()
            await barrier.wait()
            return "done"

        task1 = asyncio.create_task(bh.call(slow_task))
        task2 = asyncio.create_task(bh.call(slow_task))

        # Wait for both tasks to acquire their slots
        await asyncio.wait_for(release.wait(), timeout=1.0)
        await asyncio.sleep(0.05)

        # Third call should be rejected (fail-fast)
        with pytest.raises(BulkheadFullError) as exc_info:
            await bh.call(slow_task)

        assert "test" in str(exc_info.value)

        # Release the held slots
        barrier.set()
        await asyncio.gather(task1, task2)

    async def test_available_slots_decrements_during_execution(self):
        bh = Bulkhead("test", concurrency_limit=3, queue_timeout=None)

        barrier = asyncio.Event()
        release = asyncio.Event()

        async def slow_task():
            release.set()
            await barrier.wait()
            return "done"

        task = asyncio.create_task(bh.call(slow_task))
        await asyncio.wait_for(release.wait(), timeout=1.0)

        assert bh.active_calls == 1
        assert bh.available_slots == 2

        barrier.set()
        await task
        assert bh.active_calls == 0
        assert bh.available_slots == 3

    async def test_queued_call_succeeds_when_slot_freed(self):
        bh = Bulkhead("test", concurrency_limit=1, queue_timeout=1.0)

        done_order = []
        barrier = asyncio.Event()

        async def first_task():
            done_order.append("first")
            barrier.set()
            return "first"

        async def second_task():
            done_order.append("second")
            return "second"

        t1 = asyncio.create_task(bh.call(first_task))
        await asyncio.wait_for(barrier.wait(), timeout=1.0)
        t2 = asyncio.create_task(bh.call(second_task))

        results = await asyncio.gather(t1, t2)
        assert set(results) == {"first", "second"}

    async def test_invalid_limit_raises(self):
        with pytest.raises(ValueError, match="concurrency_limit"):
            Bulkhead("test", concurrency_limit=0)

    async def test_exception_propagates_and_slot_released(self):
        bh = Bulkhead("test", concurrency_limit=1, queue_timeout=None)

        async def bad_task():
            raise ValueError("oops")

        with pytest.raises(ValueError, match="oops"):
            await bh.call(bad_task)

        # Slot must be released after exception
        assert bh.active_calls == 0

        async def ok_task():
            return "recovered"

        result = await bh.call(ok_task)
        assert result == "recovered"
