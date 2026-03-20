# Issue #340 — Cosmos container `search_enriched_products`

## Summary

Issue #340 requests provisioning of the Cosmos DB container `search_enriched_products` in shared infrastructure.

Status: **Implemented and live in dev**.

## Infrastructure definition evidence

Source file: `.infra/modules/shared-infrastructure/shared-infrastructure.bicep`

`cosmosContainers` includes:

- `name: 'search_enriched_products'`
- `paths: ['/categoryId']`

This matches the issue requirements for container name and partition key.

## Azure live validation evidence (dev)

Subscription: `150e82e8-25db-4f1a-8e04-a2f6a77d26c4`
Resource Group: `holidaypeakhub405-dev-rg`
Cosmos account: `holidaypeakhub405-dev-cosmos`
Database: `holiday-peak-db`

Command evidence:

```bash
az cosmosdb sql container show \
  -g holidaypeakhub405-dev-rg \
  -a holidaypeakhub405-dev-cosmos \
  -d holiday-peak-db \
  -n search_enriched_products \
  --query "{id:id,partitionKey:resource.partitionKey.paths,defaultTtl:resource.defaultTtl,indexingMode:resource.indexingPolicy.indexingMode}" \
  -o json
```

Observed result:

- `partitionKey`: `['/categoryId']`
- `defaultTtl`: `null` (no TTL / permanent retention)
- container resource ID present under `.../containers/search_enriched_products`

## Managed identity access evidence

AKS cluster identity principal ID:

```bash
az aks show -g holidaypeakhub405-dev-rg -n holidaypeakhub405-dev-aks --query "identity.principalId" -o tsv
```

Result: `eaf2c803-76ad-402b-bb1b-8441559cde57`

Cosmos SQL role assignment lookup:

```bash
az cosmosdb sql role assignment list \
  -g holidaypeakhub405-dev-rg \
  -a holidaypeakhub405-dev-cosmos \
  --query "[?principalId=='eaf2c803-76ad-402b-bb1b-8441559cde57'].{roleDefinitionId:roleDefinitionId,scope:scope,principalId:principalId,id:id}" \
  -o json
```

Observed result:

- Assignment exists for principal `eaf2c803-76ad-402b-bb1b-8441559cde57`
- Role definition ends with `.../sqlRoleDefinitions/00000000-0000-0000-0000-000000000002`
- This role is Cosmos DB Built-in Data Contributor

## Acceptance criteria mapping

- Container added to Bicep template: ✅
- Deployment succeeds in dev environment: ✅ (container exists live in dev account)
- Container accessible from AKS services via managed identity: ✅ (Cosmos data-plane role assignment exists for AKS cluster identity)
