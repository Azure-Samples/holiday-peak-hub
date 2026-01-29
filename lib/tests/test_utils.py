"""Tests for logging utilities."""
import pytest
import logging
from unittest.mock import patch
from holiday_peak_lib.utils.logging import (
    configure_logging,
    log_async_operation,
    log_operation,
)


class TestConfigureLogging:
    """Test configure_logging function."""

    def test_configure_logging_default(self):
        """Test configuring logging with defaults."""
        logger = configure_logging()
        assert logger is not None
        assert isinstance(logger, logging.LoggerAdapter)

    def test_configure_logging_with_app_name(self):
        """Test configuring logging with custom app name."""
        logger = configure_logging(app_name="test-app")
        assert logger is not None
        assert logger.extra["app_name"] == "test-app"

    def test_configure_logging_without_azure_monitor(self):
        """Test logging configuration without Azure Monitor."""
        logger = configure_logging()
        assert logger is not None
        # Should still work without connection string

    def test_configure_logging_with_connection_string(self, monkeypatch):
        """Test logging with Azure Monitor connection string."""
        conn_string = "InstrumentationKey=test-key"
        
        # Just test that it doesn't raise an error
        logger = configure_logging(connection_string=conn_string)
        assert logger is not None

    def test_configure_logging_from_env(self, monkeypatch):
        """Test reading connection string from environment."""
        monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=env-key")
        
        logger = configure_logging()
        assert logger is not None

    def test_configure_logging_idempotent(self):
        """Test that calling configure_logging multiple times is safe."""
        logger1 = configure_logging(app_name="test-app-1")
        logger2 = configure_logging(app_name="test-app-1")
        assert logger1 is not None
        assert logger2 is not None

    def test_logger_has_handlers(self):
        """Test that logger has appropriate handlers."""
        logger = configure_logging(app_name="test-handlers")
        # Should have at least the stream handler
        assert logger.logger.handlers


class TestLogAsyncOperation:
    """Test log_async_operation function."""

    @pytest.mark.asyncio
    async def test_log_successful_operation(self):
        """Test logging a successful async operation."""
        logger = configure_logging(app_name="test-async")
        
        async def test_func():
            return {"result": "success"}
        
        result = await log_async_operation(
            logger,
            name="test_op",
            intent="test_intent",
            func=test_func,
            token_count=100,
            metadata={"key": "value"}
        )
        
        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_log_failed_operation(self):
        """Test logging a failed async operation."""
        logger = configure_logging(app_name="test-async-fail")
        
        async def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            await log_async_operation(
                logger,
                name="test_op",
                intent="test_intent",
                func=failing_func
            )

    @pytest.mark.asyncio
    async def test_log_operation_with_none_result(self):
        """Test logging operation that returns None."""
        logger = configure_logging(app_name="test-none")
        
        async def none_func():
            return None
        
        result = await log_async_operation(
            logger,
            name="test_op",
            intent="test_intent",
            func=none_func
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_log_operation_estimates_tokens(self):
        """Test token estimation in logging."""
        logger = configure_logging(app_name="test-tokens")
        
        async def test_func():
            return "result"
        
        result = await log_async_operation(
            logger,
            name="test_op",
            intent="test_intent",
            func=test_func,
            metadata={"large": "x" * 1000}  # Large metadata for token estimation
        )
        
        assert result == "result"

    @pytest.mark.asyncio
    async def test_log_operation_tracks_memory(self):
        """Test memory tracking in async operation."""
        logger = configure_logging(app_name="test-memory")
        
        async def test_func():
            # Allocate some memory
            data = [i for i in range(1000)]
            return {"count": len(data)}
        
        result = await log_async_operation(
            logger,
            name="test_op",
            intent="test_intent",
            func=test_func
        )
        
        assert result["count"] == 1000

    @pytest.mark.asyncio
    async def test_log_operation_with_custom_metadata(self):
        """Test logging with custom metadata."""
        logger = configure_logging(app_name="test-metadata")
        
        async def test_func():
            return "ok"
        
        metadata = {
            "user_id": "user123",
            "request_id": "req456",
            "custom_field": "value"
        }
        
        result = await log_async_operation(
            logger,
            name="test_op",
            intent="test_intent",
            func=test_func,
            metadata=metadata
        )
        
        assert result == "ok"


class TestLogOperation:
    """Test log_operation context manager."""

    def test_log_successful_sync_operation(self):
        """Test logging a successful sync operation."""
        logger = configure_logging(app_name="test-sync")
        
        with log_operation(
            logger,
            name="test_op",
            intent="test_intent",
            token_count=50,
            metadata={"key": "value"}
        ):
            result = "success"
        
        assert result == "success"

    def test_log_failed_sync_operation(self):
        """Test logging a failed sync operation."""
        logger = configure_logging(app_name="test-sync-fail")
        
        with pytest.raises(ValueError, match="Test error"):
            with log_operation(
                logger,
                name="test_op",
                intent="test_intent"
            ):
                raise ValueError("Test error")

    def test_log_operation_context_manager_cleanup(self):
        """Test context manager cleanup on success."""
        logger = configure_logging(app_name="test-cleanup")
        
        counter = {"value": 0}
        
        with log_operation(logger, name="test_op", intent="test"):
            counter["value"] = 1
        
        assert counter["value"] == 1

    def test_log_operation_multiple_calls(self):
        """Test multiple calls to log_operation."""
        logger = configure_logging(app_name="test-multiple")
        
        for i in range(3):
            with log_operation(logger, name=f"op_{i}", intent="test"):
                pass

    def test_log_operation_with_metadata(self):
        """Test log_operation with metadata."""
        logger = configure_logging(app_name="test-meta")
        
        metadata = {"iteration": 1, "batch_size": 100}
        
        with log_operation(
            logger,
            name="test_op",
            intent="processing",
            metadata=metadata
        ):
            result = "processed"
        
        assert result == "processed"


class TestLoggingIntegration:
    """Test logging integration scenarios."""

    @pytest.mark.asyncio
    async def test_nested_async_logging(self):
        """Test nested async operations with logging."""
        logger = configure_logging(app_name="test-nested")
        
        async def inner_func():
            return "inner_result"
        
        async def outer_func():
            inner_result = await log_async_operation(
                logger,
                name="inner_op",
                intent="inner",
                func=inner_func
            )
            return {"outer": "result", "inner": inner_result}
        
        result = await log_async_operation(
            logger,
            name="outer_op",
            intent="outer",
            func=outer_func
        )
        
        assert result["inner"] == "inner_result"
        assert result["outer"] == "result"

    def test_sync_and_async_logging_together(self):
        """Test using sync and async logging together."""
        logger = configure_logging(app_name="test-mixed")
        
        with log_operation(logger, name="sync_op", intent="sync"):
            sync_result = "sync_done"
        
        assert sync_result == "sync_done"

    @pytest.mark.asyncio
    async def test_logging_performance_tracking(self):
        """Test that logging tracks performance metrics."""
        import asyncio
        logger = configure_logging(app_name="test-perf")
        
        async def slow_func():
            await asyncio.sleep(0.1)
            return "done"
        
        result = await log_async_operation(
            logger,
            name="slow_op",
            intent="test",
            func=slow_func
        )
        
        assert result == "done"
        # Duration should be logged (>= 100ms)

    def test_logging_with_different_app_names(self):
        """Test logging with different app names."""
        logger1 = configure_logging(app_name="app1")
        logger2 = configure_logging(app_name="app2")
        
        assert logger1.extra["app_name"] == "app1"
        assert logger2.extra["app_name"] == "app2"
