# Azure Copilot Instructions (Project-Specific)

## General
- Use Bicep for IaC; prefer Azure Verified Modules (AVM) when available.
- Keep resource names deterministic and consistent with project naming conventions.
- Split resources into resource groups: core, data, apps, identity (per architecture docs).
- Use eastus for dev unless explicitly overridden.

## Security & Compliance
- Enable HTTPS-only and minimum TLS 1.2+ for all services.
- Prefer managed identities over secrets.
- Store secrets in Key Vault; do not emit secrets in outputs.
- Enable RBAC where supported.

## Observability
- Provision Log Analytics and Application Insights for all app workloads.
- Wire diagnostics to the Log Analytics workspace.

## Networking
- Public endpoints are acceptable for dev only.
- Add private endpoints and restrict public access for prod.

## Data
- Cosmos DB: serverless allowed for dev; ensure partition key alignment with access patterns.
- Redis: disable non-SSL; enforce TLS 1.2+.
- Storage: block public blob access, use private containers.

## Deployment
- Use the `.infra` CLI and scripts for builds and deployment.
- Keep infra documentation updated in docs/architecture.

## Outputs
- Output only non-sensitive identifiers and resource IDs.