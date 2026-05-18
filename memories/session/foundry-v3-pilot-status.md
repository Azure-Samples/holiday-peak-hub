# Foundry V3 hosted-agents pilot — RESOLVED (2026-05-18)

> **Status: RESOLVED.** `inventory-health-check` v20 (Foundry hosted agent) is **active and invokable** end-to-end on canonical ACR `holidaypeakhub405devacr`. Three operational misconfigurations had to be corrected on the registry and the project; once they were, the agent registered and responded with a 200 OK to a real Responses API call.

## Final outcome

- Active hosted agent: `inventory-health-check:20`
- Image (canonical ACR): `holidaypeakhub405devacr.azurecr.io/inventory-health-check@sha256:d4775cdf179a4c4d234cd71646a037d448081bee88f557d4bd1a1ee615d85512` (tag `foundry-v6`, build run `cj28`)
- Successful invocation: HTTP 200, `Foundry storage POST .../storage/responses -> 201`, `agent_handle_success` trace in App Insights.
- Sample response (prompt = `"ping"`):
  ```json
  {"error": "sku is required", "hint": "Provide a SKU id in the prompt, e.g. 'check health for SKU-1234'.", "input": "ping"}
  ```
  — domain validation working as designed. The richer SKU prompt returns `status=failed` only because Cosmos/Redis/EventHub/CRUD env vars are wired to `none` for the pilot; the agent itself, its storage, and the platform path are all healthy.

## Three root causes (in order of discovery)

### 1. ACR Azure-AD authentication-as-ARM policy was disabled

Foundry hosted-agents pull images by exchanging an ARM-audience AAD token for an ACR data-plane token. If the ACR has `policies.azureAdAuthenticationAsArmPolicy.status = disabled`, the exchange is rejected and the platform reports the generic `ImageError: Failed to pull container image …` — with **zero pull attempts recorded on the ACR**, which made it hard to pinpoint.

| Registry | Region | SKU | `azureAdAuthenticationAsArmPolicy` | Pull works? |
|---|---|---|---|---|
| `holidaypeakhub405devacr` (canonical) | centralus | Premium | **disabled** → fixed to **enabled** | now ✅ |
| `hphtestacr95876` (test) | westus3 | Standard | enabled (default) | ✅ |

Fix (idempotent, one-time per registry):

```powershell
az acr config authentication-as-arm update --registry holidaypeakhub405devacr --status enabled
```

The canonical ACR was created out-of-band (no Bicep resource definition in `infra/`), so the persistent fix lives on the resource itself. If the ACR is ever rebuilt from IaC, add the property:

```bicep
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  // …
  properties: {
    policies: {
      azureADAuthenticationAsArmPolicy: { status: 'enabled' }
    }
  }
}
```

### 2. AI-account managed identity needed AcrPull on the canonical ACR

The docs call out "the project MI needs Container Registry Repository Reader", but in practice the **AI-account** system MI (`351cdb70-0600-4c8c-b7f2-c6bf92ae1089`) also performs pull-side work for hosted agents. The test ACR had this MI granted; the canonical ACR did not.

Fix (idempotent):

```powershell
$acrId = "/subscriptions/150e82e8-25db-4f1a-8e04-a2f6a77d26c4/resourceGroups/holidaypeakhub405-dev-rg/providers/Microsoft.ContainerRegistry/registries/holidaypeakhub405devacr"
az role assignment create --assignee-object-id 351cdb70-0600-4c8c-b7f2-c6bf92ae1089 --assignee-principal-type ServicePrincipal --role "AcrPull" --scope $acrId
az role assignment create --assignee-object-id 351cdb70-0600-4c8c-b7f2-c6bf92ae1089 --assignee-principal-type ServicePrincipal --role "Container Registry Repository Reader" --scope $acrId
```

### 3. Per-version agent identity needed Foundry User on the project (storage 401)

When the SDK is used directly (not `azd` / VS Code), the platform-created per-version Entra identity (`instance_identity.principal_id`) is **not** auto-assigned the Foundry User role. The container would handle the request, return `agent_handle_success`, then fail to persist the response with:

```
Foundry storage POST .../storage/responses?api-version=v1 -> 401
Inbound POST /responses completed with status 500
```

Fix (idempotent — must be re-run for each new per-version MI when a new agent is created; the blueprint MI is stable across versions of the same agent):

```powershell
$projectScope = "/subscriptions/150e82e8-25db-4f1a-8e04-a2f6a77d26c4/resourceGroups/holidaypeakhub405-dev-rg/providers/Microsoft.CognitiveServices/accounts/holidaypeakhub405devais/projects/aipholidaris"
$accountScope = "/subscriptions/150e82e8-25db-4f1a-8e04-a2f6a77d26c4/resourceGroups/holidaypeakhub405-dev-rg/providers/Microsoft.CognitiveServices/accounts/holidaypeakhub405devais"
$agentMi = "<instance_identity.principal_id from get_version>"
$blueprintMi = "<blueprint.principal_id from get_version>"

az role assignment create --assignee-object-id $agentMi      --assignee-principal-type ServicePrincipal --role "Foundry User" --scope $projectScope
az role assignment create --assignee-object-id $blueprintMi  --assignee-principal-type ServicePrincipal --role "Foundry User" --scope $projectScope
az role assignment create --assignee-object-id $agentMi      --assignee-principal-type ServicePrincipal --role "Foundry User" --scope $accountScope
az role assignment create --assignee-object-id $agentMi      --assignee-principal-type ServicePrincipal --role "Cognitive Services OpenAI User" --scope $accountScope
```

> Long term: this should be done in the `deploy_hosted_agent.py` post-`create_version` step so every new version is operational without manual RBAC. Tracked as follow-up — out of scope for the pilot PR.

## Additional learnings persisted into the manifest

### `PORT` is reserved by Foundry V3

The platform now rejects it:

```
ValidationError (invalid_payload): Environment variable 'PORT' is reserved for platform use.
All FOUNDRY_* and AGENT_* variables are reserved per container-image-spec.
```

`apps/inventory-health-check/agent.hosted.yaml` now ships **without** `PORT`. The Dockerfile CMD still reads `${PORT:-${UVICORN_PORT:-8088}}`, so the platform's injected value wins automatically.

### Remote-context ACR build bypasses Windows-client upload hangs

`az acr build` from this Windows host hung on every attempt against the canonical registry. Switching to git-context bypassed the upload entirely:

```powershell
az acr build --registry holidaypeakhub405devacr `
  --image "inventory-health-check:foundry-v6" `
  --file "apps/inventory-health-check/src/Dockerfile" --target prod --no-logs `
  "https://github.com/Azure-Samples/holiday-peak-hub.git#feature/foundry-hosted-agents-pilot"
```

Build `cj28` succeeded in ~4 minutes and produced the active digest.

### GitHub Actions deploy workflow needs branch-policy escalation

`deploy-azd-inventory-health-check.yml` (and its reusable `deploy-azd.yml`) gates every job on `environment: dev`, which restricts deployments to branches matching `main` or `issue/897-*`. Adding a temporary branch policy needs **repo-admin** rights; the agent user does not have them. If we ever need to run the full workflow from a non-`main` feature branch, ask a repo admin to add a branch policy first.

## Files modified this session (post-resume)

| File | Change |
|---|---|
| [apps/inventory-health-check/agent.hosted.yaml](../../apps/inventory-health-check/agent.hosted.yaml) | Removed `PORT` env-var entry (Foundry-reserved); kept `UVICORN_PORT` as local fallback; expanded the inline comment to record the reservation. |
| [memories/session/foundry-v3-pilot-status.md](./foundry-v3-pilot-status.md) | Rewritten — pilot is RESOLVED, captures runbook for next agent. |

(Code-level fixes from earlier commit `3c137f0c` — Dockerfile CMD, lifespan logging, `/readiness` route, `_extract` Mapping branch, deploy.py `_pick_latest_version` — all remained correct; the residual gap was operational, not code.)

## Resource topology (current)

- Subscription: `150e82e8-25db-4f1a-8e04-a2f6a77d26c4` (MCAPS-Hybrid-REQ-67664-2023-rcataldi)
- Tenant: `16b3c013-d300-468d-ac64-7eda0820b6d3`
- RG: `holidaypeakhub405-dev-rg`
- AI account: `holidaypeakhub405devais` (westus3); system MI principal `351cdb70-0600-4c8c-b7f2-c6bf92ae1089`
- Project: `aipholidaris`; system MI principal `2aff93dc-52e9-4773-ba75-6fedaa651c22`
- Project endpoint: `https://holidaypeakhub405devais.services.ai.azure.com/api/projects/aipholidaris`
- App Insights: `holidaypeakhub405-dev-insights` (appId `d8eb64c4-956d-46ab-a02e-d481deadaa0b`)
- **Canonical ACR:** `holidaypeakhub405devacr` (centralus, Premium, public, **AAD-as-ARM enabled**, geo-replicated to westus3)
- Test ACR: `hphtestacr95876` (westus3, Standard) — **safe to delete** now that canonical works end-to-end.

## Runbook for the next agent

To bring a new Foundry-hosted agent up against canonical ACR:

1. **Build the image** via remote git context (skip local upload entirely):
   ```powershell
   az acr build --registry holidaypeakhub405devacr `
     --image "<agent-name>:<tag>" `
     --file "apps/<agent-name>/src/Dockerfile" --target prod --no-logs `
     "https://github.com/Azure-Samples/holiday-peak-hub.git#<branch>"
   ```
2. **Deploy via SDK** (`scripts/ops/deploy_hosted_agent.py` / `.tmp/deploy-with-tenant.ps1`).
3. **If `ImageError` on first deploy:**
   - `az acr config authentication-as-arm show --registry holidaypeakhub405devacr` — must be `enabled`.
   - `az role assignment list --scope $canonicalAcrId --assignee 351cdb70-0600-4c8c-b7f2-c6bf92ae1089` — AI-account MI must have `AcrPull` + `Container Registry Repository Reader`.
4. **If invocation returns HTTP 500 with App-Insights `storage POST -> 401`:**
   - Fetch the new version's `instance_identity.principal_id` and `blueprint.principal_id`.
   - Grant both `Foundry User` at project scope.
   - Wait ~30s for RBAC propagation and retry.
5. **Verify** with `.tmp/invoke-hosted-agent.py` and `App Insights → traces where cloud_RoleName == '<agent-name>'`.
