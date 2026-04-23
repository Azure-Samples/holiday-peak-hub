"""Machine-readable async communication contract for agent services.

Each agent declares which Event Hub topics it publishes to and consumes from,
along with the event schema types it uses. The contract is exposed via
GET /async/contract for runtime discovery.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from holiday_peak_lib.events.versioning import CURRENT_EVENT_SCHEMA_VERSION, SchemaCompatibilityPolicy


class TopicDeclaration(BaseModel):
    """A single topic that an agent publishes to or consumes from."""

    topic: str
    event_types: list[str] = Field(default_factory=list)
    description: str = ""


class AgentAsyncContract(BaseModel):
    """Self-describing async communication contract for an agent service."""

    service_name: str
    version: str = CURRENT_EVENT_SCHEMA_VERSION
    publishes: list[TopicDeclaration] = Field(default_factory=list)
    consumes: list[TopicDeclaration] = Field(default_factory=list)
    schema_policy: str = str(SchemaCompatibilityPolicy().current_version)
