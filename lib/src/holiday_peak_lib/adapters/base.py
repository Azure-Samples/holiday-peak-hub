"""Base adapter interface following Adapter pattern."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional


class BaseAdapter(ABC):
    """Abstract base adapter for retail subsystems."""

    @abstractmethod
    async def connect(self, **kwargs: Any) -> None:
        """Establish a connection to the upstream system."""

    @abstractmethod
    async def fetch(self, query: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """Fetch data from the upstream system given a query payload."""

    @abstractmethod
    async def upsert(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create or update an entity in the upstream system."""

    @abstractmethod
    async def delete(self, identifier: str) -> bool:
        """Delete an entity in the upstream system by identifier."""
