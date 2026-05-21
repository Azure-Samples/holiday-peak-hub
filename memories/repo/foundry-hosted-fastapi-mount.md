# AKS-Hosted Responses Adapter Notes

**Status**: The Foundry-managed hosted-agent pilot notes were superseded by the AKS-hosted correction.

- Product path for `inventory-health-check`: same AKS pod, same FastAPI app, same process/port as `/health`, `/ready`, `/mcp/*`, and `/invoke`.
- The Responses protocol adapter may use `agent-framework-foundry-hosting` only as an in-process `ResponsesHostServer` mount. It is not a second entry point and not Foundry-managed compute.
- Do not add `agent.hosted.yaml`, `agent.manifest.yaml`, `template.kind: hosted`, `AIProjectClient.agents.create_version`, `UVICORN_PORT=8088`, `PORT=8088`, or `HOLIDAY_PEAK_FOUNDRY_HOSTED` as a product deployment path.
- Do not disable product parity for the Responses path: Redis, Cosmos DB, Blob Storage, Event Hubs, Key Vault, and Application Insights wiring stay the same as the AKS `/invoke` path.
- Canonical files: `lib/src/holiday_peak_lib/agents/hosted.py` exposes `mount_responses_adapter`; `BaseRetailAgent.serve_responses()` is the primary API. The legacy `mount_hosted_agent`, `serve_hosted`, and `hosted_request_from_text` names are compatibility aliases only.
- `apps/inventory-health-check/agent.yaml` remains the portal-tracking/direct-model artifact and may declare `responses 1.0.0` for the AKS-hosted adapter.

