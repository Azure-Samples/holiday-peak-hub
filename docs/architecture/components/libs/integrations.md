# Integrations

Connector framework for external enterprise systems (PIM, DAM, inventory, CRM, commerce, analytics).

## Purpose

`holiday_peak_lib.integrations` provides:

- Canonical connector contracts used across apps.
- Strongly typed domain payloads (`ProductData`, `AssetData`, etc.).
- Runtime connector registration and lookup via `ConnectorRegistry`.
- Vendor-agnostic connector implementations that satisfy base contracts.

## Key Modules

- `contracts.py`
  - Defines connector base classes (`PIMConnectorBase`, `DAMConnectorBase`, etc.).
  - Defines shared payload models (`ProductData`, `AssetData`, `InventoryData`, ...).

- `registry.py`
  - `ConnectorRegistration`: metadata for registered connector instances.
  - `ConnectorRegistry`: lookup and lifecycle management for connectors.

- `pim_generic_rest.py`
  - `PIMConnectionConfig`: auth, endpoint, field-mapping, pagination, retry and rate-limit config.
  - `GenericRestPIMConnector`: concrete REST PIM connector with async I/O, token-bucket throttling, retry/backoff, and bidirectional field mapping.

## Design Rules

- Async-first I/O (`httpx.AsyncClient`).
- No hardcoded credentials; auth secrets are injected at runtime.
- Reusable connectors must implement contract interfaces and return canonical models.
- Keep connector logic lightweight and deterministic; map external schema to internal contracts in one place.

## Documentation Requirements for New Connectors

When adding any new connector under `lib/src/holiday_peak_lib/integrations/`:

1. Export it in `integrations/__init__.py`.
2. Add or update unit tests in `lib/tests/`.
3. Add a section in this document listing:
   - connector class/config names,
   - supported auth types,
   - supported operations,
   - notable resilience behavior (retry/rate-limit/circuit breaker).
4. If connector capabilities affect roadmap status, update `docs/IMPLEMENTATION_ROADMAP.md`.

## Current Connector Coverage

- Generic REST PIM:
  - Auth: bearer, basic, api_key, oauth2 (pre-fetched token).
  - Operations: get/list/search products, fetch categories, fetch product assets, push enrichment.
  - Resilience: token-bucket rate limit + exponential retry for 429/5xx and transport errors.

## Multi-Tenant Connector Configuration

`holiday_peak_lib.connectors` provides tenant-aware connector configuration and resolution:

- `tenant_config.py`
  - `TenantConfigStore` loads per-tenant files from `connectors/config/tenant-{tenantId}.yaml`.
  - Supports environment variable overrides per connector/domain.
  - Resolves Azure Key Vault references for tenant-isolated secrets.

- `tenant_resolver.py`
  - `TenantResolver` resolves tenant context from request headers/query/default.
  - `TenantContextMiddleware` propagates tenant context through request state and async context.
  - `TenantConnectorResolver` caches connector instances by tenant/domain/vendor pool key.

Recommended env override format:

- `TENANT_<TENANT_ID>_CONNECTOR_<DOMAIN>_<SETTING>=value`
- `CONNECTOR_<DOMAIN>_<SETTING>=value`
