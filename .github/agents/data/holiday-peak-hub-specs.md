# Holiday Peak Hub — Implementation Specifications

Detailed implementation specs for architecture patterns Issues #79–#84.
Consumed by **The Architect** agent when working on the `holiday-peak-hub` repository.

---

## Connector Registry Pattern (#79)

**Location**: `lib/src/holiday_peak_lib/connectors/registry.py`

Enhance existing `ConnectorRegistry` with:

- **Plugin discovery**: Auto-discover connectors at startup via entry points or config
- **Health monitoring**: Periodic connectivity checks with circuit breaker state
- **Request routing**: Route to appropriate connector by domain + tenant
- **Graceful degradation**: Fallback to cached data when connectors fail

```python
class ConnectorRegistry:
    async def register(self, connector: BaseAdapter, domain: str, config: ConnectorConfig) -> None: ...
    async def discover(self) -> list[ConnectorInfo]: ...
    async def get(self, domain: str, tenant_id: str | None = None) -> BaseAdapter: ...
    async def health_check(self) -> dict[str, HealthStatus]: ...
    async def unregister(self, connector_id: str) -> None: ...
```

Integrate with:

- `BaseAdapter` resilience patterns (circuit breakers, retries)
- Configuration loader for YAML/env-based connector settings
- FastAPI `app.state` for runtime access

---

## Event-Driven Connector Sync (#80)

**Location**: `lib/src/holiday_peak_lib/events/connector_events.py` + `apps/crud-service/src/consumers/`

Implement:

- **Event schemas**: `ProductChanged`, `InventoryUpdated`, `CustomerUpdated`, `OrderStatusChanged`, `PriceUpdated`
- **Webhook receivers** in CRUD service for external system push
- **Event Hub consumers** for async processing
- **Idempotency**: Deduplicate events by `event_id + source_system`
- **Dead-letter queue**: Handle failed events
- **Event replay**: Re-process events from checkpoint

Event flow: External webhook → Event Hub → CRUD consumer → Local update → Domain event → Downstream agents

---

## Multi-Tenant Connector Config (#81)

**Location**: `lib/src/holiday_peak_lib/connectors/tenant_config.py` + `tenant_resolver.py`

Implement:

- **Tenant context**: `TenantContext` model flows through request middleware
- **Connector resolution**: Registry resolves connector by `(tenant_id, domain)`
- **Credential isolation**: Per-tenant secrets via Azure Key Vault references
- **Connection pooling**: Shared pools per connector instance
- **Configuration schema**: `connectors/config/tenant-{tenantId}.yaml`

```python
class TenantResolver:
    async def resolve(self, request: Request) -> TenantContext: ...
    async def get_connector(self, tenant_id: str, domain: str) -> BaseAdapter: ...
```

---

## Protocol Interface Evolution (#82)

**Location**: `lib/src/holiday_peak_lib/connectors/common/versioning.py`

Implement:

- **Protocol versioning**: `PIMConnectorProtocol_v1`, `PIMConnectorProtocol_v2` with inheritance
- **Version negotiation**: Client requests specific version, server responds with compatible version
- **Adapter wrappers**: `VersionedAdapter` translates between protocol versions
- **Deprecation logging**: Warn when deprecated versions are used
- **Migration helpers**: Utility to diff protocol versions

---

## Internal Data Enrichment Guardrails (#83)

**Location**: `lib/src/holiday_peak_lib/agents/guardrails/`

**CRITICAL**: AI agents must NEVER generate product content without source data.

Implement:

- **`GuardrailMiddleware`**: Wraps enrichment agent calls
  - Validates source data IDs are present in every enrichment request
  - Rejects requests with no source data (returns "enrichment not available")
  - Logs source data used for each enrichment (audit trail)
  - Tags enriched content with source references
- **`SourceValidator`**: Checks that referenced source data exists in PIM/DAM
- **`ContentAttributor`**: Tags all agent outputs with `source_system`, `source_id`, `confidence`

```python
class GuardrailMiddleware:
    async def validate_enrichment_request(self, request: dict) -> dict | None: ...
    async def attribute_output(self, output: dict, sources: list[SourceRef]) -> dict: ...
    async def audit_enrichment(self, request: dict, output: dict, sources: list[SourceRef]) -> None: ...
```

---

## Reference Architecture Patterns (#84)

**Location**: `docs/architecture/reference/`

Document 3 reference architectures with Mermaid diagrams:

1. **PIM + DAM + Search**: Product data → AI enrichment → Azure AI Search index
2. **Omnichannel Inventory**: Real-time ATP across all channels (store + DC + vendor)
3. **Customer 360**: Unified customer view from CRM, loyalty, transactions

Each includes: architecture diagram, data flow, required connectors, sample config, deployment scripts.
