"""Unit tests for the sliding-window rate limiter."""

import asyncio

import pytest
from holiday_peak_lib.utils.rate_limiter import RateLimiter, RateLimitExceededError


@pytest.mark.asyncio
class TestRateLimiter:
    """Tests for RateLimiter."""

    async def test_allows_requests_within_limit(self):
        rl = RateLimiter(limit=5, window_seconds=60.0)
        for _ in range(5):
            await rl.check("tenant-a")  # Should not raise

    async def test_raises_when_limit_exceeded(self):
        rl = RateLimiter(limit=3, window_seconds=60.0)
        for _ in range(3):
            await rl.check("tenant-a")

        with pytest.raises(RateLimitExceededError) as exc_info:
            await rl.check("tenant-a")

        assert "tenant-a" in str(exc_info.value)
        assert exc_info.value.tenant_id == "tenant-a"
        assert exc_info.value.limit == 3

    async def test_tenants_are_isolated(self):
        rl = RateLimiter(limit=2, window_seconds=60.0)
        await rl.check("tenant-a")
        await rl.check("tenant-a")

        # tenant-b starts fresh
        await rl.check("tenant-b")
        await rl.check("tenant-b")

        # tenant-a is exhausted
        with pytest.raises(RateLimitExceededError):
            await rl.check("tenant-a")

        # tenant-b is also exhausted independently
        with pytest.raises(RateLimitExceededError):
            await rl.check("tenant-b")

    async def test_window_slides_and_allows_new_requests(self):
        rl = RateLimiter(limit=2, window_seconds=0.1)
        await rl.check("tenant-a")
        await rl.check("tenant-a")

        # Should be rate-limited now
        with pytest.raises(RateLimitExceededError):
            await rl.check("tenant-a")

        # Wait for window to slide
        await asyncio.sleep(0.15)

        # Should be allowed again
        await rl.check("tenant-a")

    async def test_remaining_returns_correct_count(self):
        rl = RateLimiter(limit=5, window_seconds=60.0)
        assert await rl.remaining("tenant-a") == 5

        await rl.check("tenant-a")
        await rl.check("tenant-a")
        assert await rl.remaining("tenant-a") == 3

    async def test_reset_single_tenant(self):
        rl = RateLimiter(limit=2, window_seconds=60.0)
        await rl.check("tenant-a")
        await rl.check("tenant-a")

        rl.reset("tenant-a")
        # Counter should be cleared
        assert await rl.remaining("tenant-a") == 2

    async def test_reset_all_tenants(self):
        rl = RateLimiter(limit=2, window_seconds=60.0)
        await rl.check("tenant-a")
        await rl.check("tenant-b")

        rl.reset()
        assert await rl.remaining("tenant-a") == 2
        assert await rl.remaining("tenant-b") == 2

    async def test_invalid_limit_raises(self):
        with pytest.raises(ValueError, match="limit"):
            RateLimiter(limit=0)

    async def test_invalid_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimiter(limit=10, window_seconds=0)
