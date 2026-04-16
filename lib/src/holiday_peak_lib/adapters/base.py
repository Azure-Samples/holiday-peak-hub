"""
Adapter interfaces and connector helpers for agent-ready context building.

This module defines:

- `AdapterError` for consistent error propagation from adapters and connectors.
- `RateLimiter`, a token-bucket-style async rate limiter.
- `AsyncCache`, a TTL-bounded LRU cache for adapter fetch results.
- `BaseAdapter`, a resilient base that all upstream integrations inherit. It
    composes `RateLimiter`, `CircuitBreaker`, and `AsyncCache` around child
    implementations to provide rate limiting, caching, retries, timeouts, and
    circuit breaking.
- `BaseConnector`, shared fetch and mapping helpers to turn adapter payloads into
        validated domain models with bounded concurrency.

The goal is to give agents a stable, validated view of upstream systems while
keeping connector implementations lean and testable.
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from collections import OrderedDict, deque
from typing import Any, Iterable, TypeVar

from holiday_peak_lib.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
)
from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


class AdapterError(Exception):
    """Custom exception for adapter errors.

    >>> raise AdapterError("bad state")
    Traceback (most recent call last):
    ...
    AdapterError: bad state
    """


class RateLimiter:
    """Token-bucket-style async rate limiter.

    Enforces at most *max_calls* within a sliding window of *per_seconds*.

    >>> import asyncio
    >>> rl = RateLimiter(max_calls=2, per_seconds=0.5)
    >>> asyncio.run(rl.acquire())
    """

    def __init__(self, max_calls: int, per_seconds: float) -> None:
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._window: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._window and now - self._window[0] > self.per_seconds:
                self._window.popleft()
            if len(self._window) < self.max_calls:
                self._window.append(now)
                return
            wait_for = self.per_seconds - (now - self._window[0])
        await asyncio.sleep(wait_for)
        await self.acquire()


class AsyncCache:
    """TTL-bounded LRU cache for adapter fetch results.

    >>> import asyncio
    >>> cache = AsyncCache(ttl=10.0, max_size=128)
    >>> asyncio.run(cache.get(("k",))) is None
    True
    """

    def __init__(self, ttl: float, max_size: int) -> None:
        self.ttl = ttl
        self.max_size = max_size
        self._store: OrderedDict[tuple, tuple[float, list[dict[str, Any]]]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: tuple) -> list[dict[str, Any]] | None:
        if self.ttl <= 0:
            return None
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return value

    async def set(self, key: tuple, value: Iterable[dict[str, Any]]) -> None:
        if self.ttl <= 0:
            return
        async with self._lock:
            expires_at = time.monotonic() + self.ttl
            self._store[key] = (expires_at, list(value))
            self._store.move_to_end(key)
            if len(self._store) > self.max_size:
                self._store.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    @staticmethod
    def make_key(query: dict[str, Any]) -> tuple:
        return tuple(sorted(query.items()))


class BaseAdapter(ABC):
    """Abstract base adapter for retail subsystems with built-in resilience.

    Subclasses implement the ``_connect_impl`` / ``_fetch_impl`` / ``_upsert_impl``
    / ``_delete_impl`` hooks. The public methods add:

    - Rate limiting
    - In-memory caching for fetches
    - Retries with backoff and jitter
    - Per-call timeouts
    - Circuit breaking

    >>> import asyncio
    >>> class EchoAdapter(BaseAdapter):
    ...     async def _connect_impl(self, **kwargs: Any) -> None:
    ...         return None
    ...     async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
    ...         return [query]
    ...     async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    ...         return payload
    ...     async def _delete_impl(self, identifier: str) -> bool:
    ...         return True
    >>> adapter = EchoAdapter()
    >>> asyncio.run(adapter.fetch({"q": 1}))
    [{'q': 1}]
    """

    def __init__(
        self,
        *,
        max_calls: int = 10,
        per_seconds: float = 1.0,
        cache_ttl: float = 30.0,
        cache_size: int = 256,
        retries: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 1.0,
        timeout: float = 5.0,
        circuit_breaker_threshold: int = 5,
        circuit_reset_seconds: float = 30.0,
    ) -> None:
        self._retries = retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._timeout = timeout

        self._rate_limiter = RateLimiter(max_calls, per_seconds)
        self._circuit_breaker = CircuitBreaker(
            name=type(self).__name__,
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_reset_seconds,
        )
        self._cache = AsyncCache(cache_ttl, cache_size)

    # Public methods (resilient wrappers)
    async def connect(self, **kwargs: Any) -> None:
        await self._connect_impl(**kwargs)

    async def fetch(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        key = self._cache_key(query)
        cached = await self._cache.get(key)
        if cached is not None:
            return cached

        async def op():
            return await self._fetch_impl(query)

        result = await self._call_with_resilience(op)
        await self._cache.set(key, result)
        return result

    async def upsert(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        async def op():
            return await self._upsert_impl(payload)

        result = await self._call_with_resilience(op)
        await self._cache.clear()
        return result

    async def delete(self, identifier: str) -> bool:
        async def op():
            return await self._delete_impl(identifier)

        result = await self._call_with_resilience(op)
        await self._cache.clear()
        return result

    # Protected hooks to implement
    @abstractmethod
    async def _connect_impl(self, **kwargs: Any) -> None:
        """Establish a connection to the upstream system."""

    @abstractmethod
    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        """Fetch data from the upstream system given a query payload."""

    @abstractmethod
    async def _upsert_impl(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Create or update an entity in the upstream system."""

    @abstractmethod
    async def _delete_impl(self, identifier: str) -> bool:
        """Delete an entity in the upstream system by identifier."""

    # Resilience helpers
    async def _call_with_resilience(self, func):
        await self._rate_limiter.acquire()

        last_error: Exception | None = None
        for attempt in range(1, self._retries + 2):
            try:

                async def _timed_call() -> Any:
                    return await asyncio.wait_for(func(), timeout=self._timeout)

                result = await self._circuit_breaker.call(_timed_call)
                return result
            except CircuitBreakerOpenError as exc:
                raise AdapterError("Circuit breaker open") from exc
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt > self._retries:
                    break
                delay = min(self._max_delay, self._base_delay * (2 ** (attempt - 1)))
                delay *= 1 + random.random() * 0.25
                await asyncio.sleep(delay)
        raise AdapterError("Operation failed after retries") from last_error

    def resilience_status(self) -> dict[str, Any]:
        """Return current resilience/circuit-breaker state for observability."""
        return {
            "failure_count": self._circuit_breaker.failure_count,
            "circuit_open": self._circuit_breaker.state.value == "open",
            "threshold": self._circuit_breaker.failure_threshold,
            "reset_seconds": self._circuit_breaker.recovery_timeout,
        }

    def _cache_key(self, query: dict[str, Any]) -> tuple:
        """Build a hashable cache key from *query*. Override for custom keys."""
        return AsyncCache.make_key(query)


class BaseConnector:
    """Base connector with shared adapter access and mapping utilities.

    Use this to normalize adapter payloads into Pydantic models with consistent
    validation and error handling. Example with a tiny stub adapter::

        >>> import asyncio
        >>> class StubAdapter(BaseAdapter):
        ...     async def _connect_impl(self, **kwargs: Any):
        ...         return None
        ...     async def _fetch_impl(self, query: dict[str, Any]):
        ...         return [{"value": 1}]
        ...     async def _upsert_impl(self, payload: dict[str, Any]):
        ...         return payload
        ...     async def _delete_impl(self, identifier: str) -> bool:
        ...         return True
        >>> class Model(BaseModel):
        ...     value: int
        >>> connector = BaseConnector(adapter=StubAdapter())
        >>> asyncio.run(connector._fetch_first(name="x"))
        {'value': 1}
        >>> asyncio.run(connector._map_single(Model, {"value": "1"})).value
        1
    """

    def __init__(self, adapter: BaseAdapter | None = None, map_concurrency: int = 10) -> None:
        """Initialize with an optional adapter and mapping concurrency limit.

        >>> BaseConnector(map_concurrency=0)._map_semaphore._value
        1
        >>> isinstance(BaseConnector().adapter, BaseAdapter)
        Traceback (most recent call last):
        ...
        AdapterError: Adapter has not been configured.
        """
        self._adapter: BaseAdapter | None = adapter
        self._map_semaphore = asyncio.Semaphore(max(1, map_concurrency))

    @property
    def adapter(self) -> BaseAdapter:
        """Return the configured adapter, raising if none is set.

        >>> connector = BaseConnector()
        >>> connector.adapter
        Traceback (most recent call last):
        ...
        AdapterError: Adapter has not been configured.
        """
        adapter = self._adapter
        if adapter is None:
            raise AdapterError("Adapter has not been configured.")
        return adapter

    @adapter.setter
    def adapter(self, adapter: BaseAdapter) -> None:
        """Set or replace the adapter instance."""
        self._adapter = adapter

    async def connect(self, **kwargs: Any) -> None:
        """Open a connection using the underlying adapter."""
        await self.adapter.connect(**kwargs)

    async def _fetch_first(self, **query: Any) -> dict[str, Any] | None:
        """Return the first record that matches the query, if present.

        >>> class OneAdapter(BaseAdapter):
        ...     async def _connect_impl(self, **kwargs: Any):
        ...         return None
        ...     async def _fetch_impl(self, query: dict[str, Any]):
        ...         return [{"value": 1}]
        ...     async def _upsert_impl(self, payload: dict[str, Any]):
        ...         return payload
        ...     async def _delete_impl(self, identifier: str) -> bool:
        ...         return True
        >>> connector = BaseConnector(adapter=OneAdapter())
        >>> asyncio.run(connector._fetch_first())
        {'value': 1}
        """
        records = await self._fetch_many(**query)
        return records[0] if records else None

    async def _fetch_many(self, **query: Any) -> list[dict[str, Any]]:
        """Execute adapter fetch and coerce results into a list.

        >>> class TwoAdapter(BaseAdapter):
        ...     async def _connect_impl(self, **kwargs: Any):
        ...         return None
        ...     async def _fetch_impl(self, query: dict[str, Any]):
        ...         return [{"value": 1}, {"value": 2}]
        ...     async def _upsert_impl(self, payload: dict[str, Any]):
        ...         return payload
        ...     async def _delete_impl(self, identifier: str) -> bool:
        ...         return True
        >>> connector = BaseConnector(adapter=TwoAdapter())
        >>> asyncio.run(connector._fetch_many())
        [{'value': 1}, {'value': 2}]
        """
        try:
            raw: Iterable[dict[str, Any]] = await self.adapter.fetch(query)
            return list(raw)
        except Exception as exc:
            raise AdapterError(f"Failed to fetch data for query: {query}") from exc

    async def _map_single(
        self, model: type[ModelT], payload: dict[str, Any] | None
    ) -> ModelT | None:
        """Validate and coerce a single payload into the target model.

        >>> class Model(BaseModel):
        ...     value: int
        >>> connector = BaseConnector()
        >>> asyncio.run(connector._map_single(Model, {"value": "3"})).value
        3
        >>> asyncio.run(connector._map_single(Model, None)) is None
        True
        >>> asyncio.run(connector._map_single(Model, {"value": "bad"}))
        Traceback (most recent call last):
        ...
        AdapterError: Invalid payload for Model
        """
        if payload is None:
            return None
        try:
            return model(**payload)
        except ValidationError as exc:
            raise AdapterError(f"Invalid payload for {model.__name__}") from exc

    async def _map_many(
        self, model: type[ModelT], payloads: Iterable[dict[str, Any]]
    ) -> list[ModelT]:
        """Normalize multiple payloads concurrently with a bounded semaphore.

        >>> class Model(BaseModel):
        ...     value: int
        >>> connector = BaseConnector()
        >>> asyncio.run(connector._map_many(Model, [{"value": 1}, {"value": "2"}]))
        [Model(value=1), Model(value=2)]
        """

        async def map_one(payload: dict[str, Any]) -> ModelT:
            async with self._map_semaphore:
                try:
                    return model(**payload)
                except ValidationError as exc:
                    raise AdapterError(f"Invalid payload for {model.__name__}") from exc

        tasks = [asyncio.create_task(map_one(payload)) for payload in payloads]
        mapped: list[ModelT] = []
        for task in asyncio.as_completed(tasks):
            mapped.append(await task)
        return mapped
