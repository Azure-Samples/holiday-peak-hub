# Per-Agent Deployment with Shared Dependencies

This guide explains how to deploy one specific agentic app while still honoring the required platform dependencies (databases, Foundry, Event Hubs, and memory services) defined in this repository.

## Scope

- Deployment model: shared infrastructure + single service deployment.
- IaC source: `.infra/azd/main.bicep` and `.infra/modules/shared-infrastructure/shared-infrastructure.bicep`.
- Service deploy source: `azure.yaml` service definitions with Helm predeploy hooks.

## What Is Provisioned Before Any Agent Deploy

Run `azd provision` once per environment to create the shared dependency layer:

- AKS cluster
- Azure AI Foundry project and model deployment outputs
- Azure Event Hubs namespace and topics
- Cosmos DB account and database
- Redis cache
- Blob Storage account
- Key Vault
- Azure AI Search service and indexes

The predeploy hooks now validate required dependency variables before rendering Kubernetes manifests:

- `.infra/azd/hooks/render-helm.sh`
- `.infra/azd/hooks/render-helm.ps1`

## One-Time Environment Provisioning

```bash
azd env new <environment>
azd env set deployShared true -e <environment>
azd env set deployStatic false -e <environment>
azd env set environment <environment> -e <environment>
azd env set location <location> -e <environment>
azd provision -e <environment>
```

## Deploy One Particular Agent

```bash
azd deploy --service <agent-service-name> -e <environment>
```

Examples:

```bash
azd deploy --service crm-profile-aggregation -e dev
azd deploy --service ecommerce-catalog-search -e dev
azd deploy --service truth-enrichment -e dev
```

## Dependency Profiles

### Profile A: Core Agent

Required shared services:

- Event Hubs namespace
- Foundry endpoint and project
- Cosmos DB account and database
- Redis host
- Blob account URL
- Key Vault URI

### Profile B: Search-Enhanced Agent

Required shared services:

- All Profile A dependencies
- AI Search endpoint, index, vector index, indexer name
- Embedding deployment name
- `search-enrichment-jobs` topic and consumer-group wiring

### Profile C: Truth Pipeline Agent

Required shared services:

- All Profile A dependencies
- Truth topic wiring per service:
- `truth-ingestion` -> `ingest-jobs` / `ingestion-group`
- `truth-enrichment` -> `enrichment-jobs` / `enrichment-engine`
- `truth-export` -> `export-jobs` / `export-engine`
- `truth-hitl` -> `hitl-jobs` / `hitl-service`

## Agent-to-Profile Map

| Agent service | Profile |
| --- | --- |
| crm-campaign-intelligence | A |
| crm-profile-aggregation | A |
| crm-segmentation-personalization | A |
| crm-support-assistance | A |
| ecommerce-cart-intelligence | A |
| ecommerce-catalog-search | B |
| ecommerce-checkout-support | A |
| ecommerce-order-status | A |
| ecommerce-product-detail-enrichment | A |
| inventory-alerts-triggers | A |
| inventory-health-check | A |
| inventory-jit-replenishment | A |
| inventory-reservation-validation | A |
| logistics-carrier-selection | A |
| logistics-eta-computation | A |
| logistics-returns-support | A |
| logistics-route-issue-detection | A |
| product-management-acp-transformation | A |
| product-management-assortment-optimization | A |
| product-management-consistency-validation | A |
| product-management-normalization-classification | A |
| search-enrichment-agent | B |
| truth-ingestion | C |
| truth-enrichment | C |
| truth-export | C |
| truth-hitl | C |

## Troubleshooting Dependency Validation Failures

If predeploy fails with missing environment variables:

1. Re-run provisioning with shared infra enabled.
2. Confirm azd environment values were exported.
3. Deploy again.

```bash
azd env get-values -e <environment>
azd provision -e <environment>
azd deploy --service <agent-service-name> -e <environment>
```

## Optional: Isolated Per-Agent IaC (Standalone Demo Mode)

For isolated demos, deploy each agent module directly instead of shared infra.

```bash
az deployment sub create \
  --name <agent>-standalone-<environment> \
  --location <location> \
  --template-file .infra/modules/<agent>/<agent>-main.bicep \
  --parameters environment=<environment>
```

Then deploy only that service with azd:

```bash
azd deploy --service <agent-service-name> -e <environment>
```

Use this mode only when isolation is required, since it duplicates resources and increases cost.
