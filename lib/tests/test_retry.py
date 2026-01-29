"""Tests for retry utilities."""
import pytest

from holiday_peak_lib.utils.retry import async_retry


@pytest.mark.asyncio
class TestAsyncRetry:
    """Tests for async_retry decorator."""

    async def test_successful_first_attempt(self):
        """Test successful execution on first try."""
        call_count = 0
        
        @async_retry(times=3, delay_seconds=0.01)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    async def test_retry_after_failures(self):
        """Test retrying after failures then succeeding."""
        call_count = 0
        
        @async_retry(times=3, delay_seconds=0.01)
        async def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "finally worked"
        
        result = await eventually_successful()
        assert result == "finally worked"
        assert call_count == 3

    async def test_exhausts_retries_and_raises(self):
        """Test that error is raised after all retries exhausted."""
        call_count = 0
        
        @async_retry(times=2, delay_seconds=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Always fails")
        
        with pytest.raises(RuntimeError, match="Always fails"):
            await always_fails()
        assert call_count == 2

    async def test_different_error_types(self):
        """Test retry with different error types."""
        @async_retry(times=3, delay_seconds=0.01)
        async def mixed_errors():
            raise ConnectionError("Network issue")
        
        with pytest.raises(ConnectionError, match="Network issue"):
            await mixed_errors()

    async def test_with_arguments(self):
        """Test decorated function with arguments."""
        call_count = 0
        
        @async_retry(times=3, delay_seconds=0.01)
        async def func_with_args(a, b, c=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return f"{a}-{b}-{c}"
        
        result = await func_with_args("x", "y", c="z")
        assert result == "x-y-z"
        assert call_count == 2
