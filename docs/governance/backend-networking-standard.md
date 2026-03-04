# Backend Networking Standard

## Scope

This standard applies to all environments and all backend services in this repository:

- Frontend (`apps/ui`)
- CRUD service (`apps/crud-service`)
- Agentic services (`apps/*` on AKS)
- Shared data dependencies (Redis, Cosmos DB, Blob Storage, PostgreSQL)

## Mandatory Rules

1. **APIM-only backend API access**
   - All client-visible backend API traffic MUST go through Azure API Management (APIM).
   - Frontend calls MUST target APIM URLs (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_CRUD_API_URL`, `NEXT_PUBLIC_AGENT_API_URL`).
   - CRUD synchronous calls to agents MUST route via APIM (`AGENT_APIM_BASE_URL`).

2. **No direct backend API access from clients**
   - Direct client calls to AKS services, pod IPs, internal DNS names (`*.svc.cluster.local`), or App Gateway backend IPs are prohibited.

3. **Private data-plane dependency connectivity**
   - Redis, Cosmos DB, Blob Storage, and PostgreSQL MUST be reachable from AKS via private networking (Private Endpoint + private DNS / VNet-integrated path).
   - Public network access for these dependencies should remain disabled unless an approved break-glass maintenance window is active.

4. **Deployment guardrails**
   - Helm render hooks MUST fail fast when required APIM/memory environment values are missing.
   - CRUD service manifests MUST render the Kubernetes service as an internal load balancer (`service.type=LoadBalancer` with `service.beta.kubernetes.io/azure-load-balancer-internal=true`) so APIM can target a stable private backend.
   - APIM CRUD backend sync MUST resolve to a load balancer endpoint and must not fall back to ClusterIP or `*.svc.cluster.local` targets.
   - For agent services, required env values include:
     - `REDIS_URL`
     - `COSMOS_ACCOUNT_URI`
     - `COSMOS_DATABASE`
     - `COSMOS_CONTAINER`
     - `BLOB_ACCOUNT_URL`
     - `BLOB_CONTAINER`
     - `CRUD_SERVICE_URL`
   - For CRUD, required env value includes:
     - `AGENT_APIM_BASE_URL`
   - For CRUD in password auth mode, `POSTGRES_USER` MUST be the PostgreSQL admin/user principal (for example `crud_admin`) and not a managed identity-style AKS principal value.

## Baseline Environment Values

At minimum, each deployed environment must define:

- `APIM_GATEWAY_URL` / `NEXT_PUBLIC_API_URL`
- `AGENT_APIM_BASE_URL`
- `REDIS_URL`
- `COSMOS_ACCOUNT_URI`
- `COSMOS_DATABASE`
- `COSMOS_CONTAINER`
- `BLOB_ACCOUNT_URL`
- `BLOB_CONTAINER`
- `CRUD_SERVICE_URL` (APIM-routed CRUD base)

## Verification Checklist

- APIM routes respond for CRUD (`/api/*`) and agents (`/agents/*`).
- Agent pods have memory env variables populated.
- CRUD has `AGENT_APIM_BASE_URL` populated.
- AKS pod DNS/TCP checks for Cosmos/Blob/Postgres/Redis succeed against private endpoints.
- Resource network posture confirms private endpoint usage and no accidental public exposure.

## Enforcement Notes

This repository enforces the standard through deployment hooks and runtime URL resolution logic. If required values are missing, deployment should fail early instead of silently degrading to non-standard routing.
