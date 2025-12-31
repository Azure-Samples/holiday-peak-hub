"""Simple retry utility."""
import asyncio
from typing import Any, Callable


def async_retry(times: int = 3, delay_seconds: float = 0.1) -> Callable:
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None
            for _ in range(times):
                try:
                    return await func(*args, **kwargs)
                except Exception as error:  # pragma: no cover - surface errors after retries
                    last_error = error
                    await asyncio.sleep(delay_seconds)
            if last_error:
                raise last_error
        return wrapper
    return decorator
