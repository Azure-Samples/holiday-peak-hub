# Foundry V3 hosted-agents pilot — SUPERSEDED (2026-05-18)

> Superseded by the AKS-hosted Responses adapter correction. The product path for `inventory-health-check` is the same AKS pod, same FastAPI app, same process/port as `/health`, `/ready`, `/mcp/*`, and `/invoke`. Do not use `agent.hosted.yaml`, Foundry-managed hosted compute, or `AIProjectClient.agents.create_version` as the product path.

## Current Target

- Keep hosted-agent protocol behavior on AKS via the in-process Responses adapter.
- Keep product dependency parity for the Responses path: Redis, Cosmos DB, Blob Storage, Event Hubs, Key Vault, and Application Insights wiring remain the AKS service wiring.
- Treat the old v20/v24 Foundry-managed validations as historical evidence only; they are not accepted deployment evidence for PR #1103 / issue #1107.
