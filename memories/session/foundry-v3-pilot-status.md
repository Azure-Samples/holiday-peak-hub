# Foundry V3 hosted-agents pilot — resume state (2026-05-15 ~12:10 UTC)

> **Status: NOT resolved.** The earlier "active" result regressed. `inventory-health-check` versions 7–10 all fail with `ImageError` despite SDK upgrade, RBAC fix, image-arch fix, ACR public-network, and a freshly-created Foundry project ContainerRegistry connection. Pause point — resume from this file.

## Original ask

> "We were implementing the change from Agents V2 to Agents V3 with hosted agent. We could make the agent show in the UI, but it is presenting this error. Investigate and correct."

**Error (still active):**
```
ImageError: Failed to pull container image. Please check the image URI and ACR permissions, then retry.
(image: holidaypeakhub405devacr.azurecr.io)
https://aka.ms/hostedagents/tsg/image
```

## Latest snapshot

- Latest attempt: **v10** of `inventory-health-check` — `status: failed` with `ImageError`, ~2s after create.
- Fresh-name probe: `inv-health-fresh-test` v1 — **also failed identically** → not a per-agent cache.
- ACR `TotalPullCount` shows **0 pulls** during every deploy window → Foundry rejects pre-pull (never reaches ACR data plane).
- All 21 unit tests pass; deploy.py Path-1 patch correctly surfaces true status.

## What is verified correct

| Check | Status |
|---|---|
| SDK `azure-ai-projects` in venv | **2.1.0** ✅ |
| `allow_preview=True` in deploy.py | ✅ (line ~140) |
| Image arch / OS | `linux/amd64` ✅ (digest `sha256:5b9d860194fa54f616c5ff6841970b354db9ed40ee7f94fbca0620011b3ac250`) |
| Image existence | ✅ (tag `foundry-v3` exists in repo `inventory-health-check`) |
| ACR public reachable | ✅ (`publicNetworkAccess=Enabled`, `defaultAction=Allow`, 0 IP rules) |
| ACR SKU / region | Premium / centralus ✅ |
| MIs with **AcrPull** (unconditional) | Project `2aff93dc-…`, Instance `e4512d94-…`, Blueprint `d4f34fe8-…` ✅ |
| MIs with **Container Registry Repository Reader** (unconditional) | Same three ✅ (created 2026-05-15 07:51 UTC) |
| Project endpoint reachable | ✅ (POST/GET 200) |
| User-Agent on requests | `azsdk-python-ai-projects/2.1.0` ✅ |
| deploy.py raises `RuntimeError` on `status=failed` | ✅ (Path 1 patch via `get_version`) |
| **NEW**: Foundry project ContainerRegistry connection | ✅ Created via REST 2026-05-15 12:04 UTC |

## Key resources

- **Subscription:** `150e82e8-25db-4f1a-8e04-a2f6a77d26c4`
- **RG:** `holidaypeakhub405-dev-rg`
- **ACR:** `holidaypeakhub405devacr` (centralus, Premium, public)
- **AI account:** `holidaypeakhub405devais` (westus3, AIServices/S0)
- **Foundry project:** `aipholidaris` (westus3)
- **Project endpoint:** `https://holidaypeakhub405devais.services.ai.azure.com/api/projects/aipholidaris`
- **Image:** `holidaypeakhub405devacr.azurecr.io/inventory-health-check:foundry-v3`

### Managed identities (all with unconditional `AcrPull` + `Container Registry Repository Reader`)

| Role | Principal ID | Client ID |
|---|---|---|
| Project MI | `2aff93dc-52e9-4773-ba75-6fedaa651c22` | — |
| Account MI | `351cdb70-9be7-4097-9be8-3b78f1a0c5d6` | — |
| Instance MI (runs container) | `e4512d94-6755-4fd1-97cf-60de45d176f3` | `e4512d94-6755-4fd1-97cf-60de45d176f3` |
| Blueprint MI | `d4f34fe8-ba6a-40c0-8b6f-117c6b758b4e` | `87f0310a-3284-404b-8705-00209d38b244` |

### Foundry project ContainerRegistry connection (created this session)

ARM resource:
```
/subscriptions/150e82e8-25db-4f1a-8e04-a2f6a77d26c4/resourceGroups/holidaypeakhub405-dev-rg/
  providers/Microsoft.CognitiveServices/accounts/holidaypeakhub405devais/projects/aipholidaris/
  connections/holidaypeakhub405devacr
```

PUT body used (`api-version=2025-04-01-preview`):
```json
{
  "properties": {
    "category": "ContainerRegistry",
    "target": "https://holidaypeakhub405devacr.azurecr.io",
    "authType": "AAD",
    "isSharedToAll": true,
    "metadata": {
      "ApiType": "Azure",
      "ResourceId": "/subscriptions/150e82e8-25db-4f1a-8e04-a2f6a77d26c4/resourceGroups/holidaypeakhub405-dev-rg/providers/Microsoft.ContainerRegistry/registries/holidaypeakhub405devacr",
      "location": "centralus"
    }
  }
}
```

Response landed with `category: ContainerRegistry`, `authType: AAD`, `isDefault: true`, `useWorkspaceManagedIdentity: false`, `isSharedToAll: false` (API ignored our `true`).

## Failed attempts (this session)

| Version | Image ref | Outcome | Notes |
|---|---|---|---|
| 1–6 | tag `foundry-v3` | `failed/ImageError` | SDK 2.0.1 in venv masked as `succeeded=True`. |
| 7 | tag `foundry-v3` | `failed/ImageError` | First with SDK 2.1.0 + Path 1 patch. |
| 8 | digest `sha256:5b9d…` | `failed/ImageError` | Digest pin — rules out tag resolution. |
| `inv-health-fresh-test` v1 | tag `foundry-v3` | `failed/ImageError` | Fresh agent name — rules out per-agent cache. |
| 9 | tag `foundry-v3` | `failed/ImageError` | 22s after creating ContainerRegistry connection. |
| 10 | tag `foundry-v3` | `failed/ImageError` | Several minutes after connection PUT. |

## Still-open hypotheses

1. **Cross-region pull.** ACR is `centralus`; project is `westus3`. Premium ACR with geo-replication should handle this, but hosted-agents preview may require co-location.
2. **Connection `useWorkspaceManagedIdentity` / `authType` shape.** Our PUT produced `authType=AAD`, `useWorkspaceManagedIdentity=false`. Maybe ACR pull needs `authType=ManagedIdentity` or `useWorkspaceManagedIdentity=true`. Schema is undocumented.
3. **Cached blueprint binding.** Blueprint `inventory-health-check-097db` was provisioned during v1 (before the connection existed). It may be bound to a pre-connection pull path. Recreate path: `project.agents.delete(agent_name='inventory-health-check')` then redeploy.
4. **ACR diagnostic-settings absent** — no Log Analytics signal for pull-stage failures. Add settings before next attempt for definitive evidence.

## Files modified this session

| File | Change |
|---|---|
| [lib/src/holiday_peak_lib/foundry_hosting/deploy.py](lib/src/holiday_peak_lib/foundry_hosting/deploy.py) | Path 1 in `_resolve_latest_version` now calls `agents.get_version(agent_name, latest_str)` (with `TypeError`→positional fallback) after `_pick_latest_version` to surface true per-version status. Outer `deploy_hosted_agent_version` raises `RuntimeError(f"hosted-agent registration failed: agent={agent_name} version={version} status={status}")` on non-`active`. |
| `.tmp/agent-fresh.yaml` | Copy of agent manifest with `inventory-health-check` → `inv-health-fresh-test`. |
| `.tmp/list-conns.ps1` | Lists Foundry project connections via ARM REST. |
| `.tmp/create-acr-conn.ps1` | PUT ContainerRegistry connection (idempotent). |
| `.tmp/deploy-{v7b,v8-digest,fresh,v9-with-conn,v10}.log` | Per-attempt deploy logs. |

## Files NOT modified

- [apps/inventory-health-check/agent.hosted.yaml](apps/inventory-health-check/agent.hosted.yaml) — unchanged.
- [scripts/ops/deploy_hosted_agent.py](scripts/ops/deploy_hosted_agent.py) — unchanged.
- [lib/tests/test_foundry_hosting_deploy.py](lib/tests/test_foundry_hosting_deploy.py) — unchanged (21 tests still pass).

## Resume plan — when we come back

### Step 1 — Sanity check (no-op cost)
```powershell
.\.tmp\list-conns.ps1
```
Confirm `name=holidaypeakhub405devacr category=ContainerRegistry` row is still present.

### Step 2 — Destructive recreate (requires user OK)

Hypothesis: existing agent/blueprint were bound to a pre-connection pull path.
```powershell
# DESTRUCTIVE — confirm with user before running
lib\src\.venv\Scripts\python.exe -c @"
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential
c = AIProjectClient(endpoint='https://holidaypeakhub405devais.services.ai.azure.com/api/projects/aipholidaris', credential=AzureCliCredential(), allow_preview=True)
c.agents.delete(agent_name='inventory-health-check')
print('deleted')
"@

# Then redeploy v1 (env-vars block from session below)
& lib\src\.venv\Scripts\python.exe scripts\ops\deploy_hosted_agent.py `
  --agent-yaml apps\inventory-health-check\agent.hosted.yaml `
  --image-uri "holidaypeakhub405devacr.azurecr.io/inventory-health-check:foundry-v3" `
  --project-endpoint "https://holidaypeakhub405devais.services.ai.azure.com/api/projects/aipholidaris" `
  --poll-interval-seconds 5 --poll-timeout-seconds 600 --log-level INFO --json *> .tmp\deploy-postwipe.log
```

If `active` → port the connection PUT into Bicep under `infra/` so all 26 agents inherit it.
If still `failed` → Step 3.

### Step 3 — Region co-location probe

Create temp Premium ACR in westus3, import the image, grant the project MI `AcrPull`, create a project ContainerRegistry connection for it, deploy. If it works → ACR must be co-located (or replicated) for hosted-agents preview.

### Step 4 — Enable ACR diagnostics (regardless)

```powershell
az monitor diagnostic-settings create `
  --resource $acrId `
  --name acr-foundry-diag `
  --workspace <log-analytics-id> `
  --logs '[{"category":"ContainerRegistryLoginEvents","enabled":true},{"category":"ContainerRegistryRepositoryEvents","enabled":true}]'
```

### Step 5 — Microsoft support ticket (if still failing after Step 3)

Use the support-ticket package below.

## Support-ticket package (paste-ready)

- **Symptom:** Hosted-agent versions in Foundry project `aipholidaris` (westus3) fail with `ImageError` ~2s after creation. ACR `TotalPullCount` shows 0 attempts during failure windows.
- **ACR:** `holidaypeakhub405devacr` (centralus, Premium, public, anonymousPull=false, dataEndpoint=false). All three relevant project MIs have unconditional `AcrPull` + `Container Registry Repository Reader`. Image is `linux/amd64`.
- **Already tried:** SDK 2.0.1 → 2.1.0; `allow_preview=True`; tag and digest references; fresh agent name; Foundry project ContainerRegistry connection created (`authType: AAD`).
- **Affected logs in `.tmp/`:** `deploy-v7b.log`, `deploy-v8-digest.log`, `deploy-fresh.log`, `deploy-v9-with-conn.log`, `deploy-v10.log`.
- **Documented error codes (none match what we see):** `image_pull_failed`, `SubscriptionIsNotRegistered`, `InvalidAcrPullCredentials`, `UnauthorizedAcrPull`, `AcrImageNotFound`, `RegistryNotFound`.
- **Ask:** root-cause the generic `ImageError` code (no documented bucket, 0 pulls observed) and confirm whether ACR must be region-co-located with the Foundry project for hosted-agents preview.

## RBAC grants previously performed (idempotent — safe to re-run)

```powershell
$acrId = "/subscriptions/150e82e8-25db-4f1a-8e04-a2f6a77d26c4/resourceGroups/holidaypeakhub405-dev-rg/providers/Microsoft.ContainerRegistry/registries/holidaypeakhub405devacr"
az role assignment create --assignee-object-id 2aff93dc-52e9-4773-ba75-6fedaa651c22 --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId  # project MI
az role assignment create --assignee-object-id 351cdb70-9be7-4097-9be8-3b78f1a0c5d6 --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId  # account MI
az role assignment create --assignee-object-id e4512d94-6755-4fd1-97cf-60de45d176f3 --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId  # instance MI
az role assignment create --assignee-object-id d4f34fe8-ba6a-40c0-8b6f-117c6b758b4e --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId  # blueprint MI

# Container Registry Repository Reader was added 2026-05-15 07:51 UTC for the same MIs
$role = "Container Registry Repository Reader"
foreach ($p in @("2aff93dc-52e9-4773-ba75-6fedaa651c22","e4512d94-6755-4fd1-97cf-60de45d176f3","d4f34fe8-ba6a-40c0-8b6f-117c6b758b4e")) {
  az role assignment create --assignee-object-id $p --assignee-principal-type ServicePrincipal --role $role --scope $acrId
}
```

## Env-vars block used for every deploy attempt

```powershell
$Env:PROJECT_ENDPOINT = "https://holidaypeakhub405devais.services.ai.azure.com/api/projects/aipholidaris"
$Env:PROJECT_NAME = "aipholidaris"
$Env:MODEL_DEPLOYMENT_NAME_FAST = "gpt-35-turbo"; $Env:MODEL_DEPLOYMENT_NAME_RICH = "gpt-4"
$Env:FOUNDRY_AGENT_ID_FAST = "none"; $Env:FOUNDRY_AGENT_ID_RICH = "none"
$Env:REDIS_HOST = "none"; $Env:REDIS_URL = "none"
$Env:COSMOS_ACCOUNT_URI = "none"; $Env:COSMOS_DATABASE = "none"; $Env:COSMOS_CONTAINER = "none"
$Env:BLOB_ACCOUNT_URL = "none"; $Env:BLOB_CONTAINER = "none"
$Env:EVENT_HUB_NAMESPACE = "none"; $Env:KEY_VAULT_URI = "none"
$Env:PYTHONUNBUFFERED = "1"
```

## Lessons learned (for future runbooks)

- **`list_versions` is denormalized** — every version reports `active` regardless of true state. Always confirm with `get_version`. (Patched in `deploy.py` Path 1.)
- **SDK 2.0.1 reports success on failure**; pin `azure-ai-projects>=2.1.0` everywhere.
- **`get_version` kwarg is `agent_version` (not `version`)**. Keep the TypeError→positional fallback.
- **PowerShell `Tee-Object` and complex pipelines buffer/truncate** process output. Use `*> file.log` redirect.
- **Venv pip is broken** here (`ModuleNotFoundError: pip._internal.operations.build`) — use `uv pip install --python lib\src\.venv\Scripts\python.exe`.
- **`az acr login --expose-token`** returns a **refresh** token, not an access token — must exchange via `/oauth2/token` for v2 API calls.
- **ACR metric `TotalLoginCount` does not exist.** Valid: `TotalPullCount`, `SuccessfulPullCount`, `TotalPushCount`, `SuccessfulPushCount`, `RunDuration`, `AgentPoolCPUTime`, `StorageUsed`.
- **`ConnectionType` enum doesn't expose `ContainerRegistry`** in `azure-ai-projects==2.1.0` — must PUT via ARM REST at `Microsoft.CognitiveServices/.../projects/connections?api-version=2025-04-01-preview`.
- **Hosted-agents permissions doc explicitly says** "A connection is created for the Azure Container Registry, which the project uses for image pulling." Without that connection, ARM RBAC alone is insufficient — Foundry pre-flight rejects the request without ever touching ACR.

## To do when resumed (in order)

1. Run `.tmp/list-conns.ps1` — confirm ACR connection is still there.
2. **Ask user:** OK to delete the existing `inventory-health-check` agent so blueprint is recreated against the new connection? (destructive)
3. If yes → delete + redeploy v1. If `active`, port the connection to Bicep in `infra/` for the other 25 agents.
4. If still failing → Step 3 (co-located westus3 ACR).
5. Enable ACR diagnostic settings (Step 4) regardless.
6. Add test `test_resolve_latest_version_uses_get_version_when_list_versions_is_denormalized` in [lib/tests/test_foundry_hosting_deploy.py](lib/tests/test_foundry_hosting_deploy.py).
7. Update this file with the resolution.
8. Cleanup `.tmp/` after PR #1103 merges (per repo temp-artifact policy).

## Cross-references

- PR: https://github.com/Azure-Samples/holiday-peak-hub/pull/1103
- Issue: #990
- Deploy script: [scripts/ops/deploy_hosted_agent.py](scripts/ops/deploy_hosted_agent.py)
- Deploy library: [lib/src/holiday_peak_lib/foundry_hosting/deploy.py](lib/src/holiday_peak_lib/foundry_hosting/deploy.py)
- Manifest: [apps/inventory-health-check/agent.hosted.yaml](apps/inventory-health-check/agent.hosted.yaml)
- Transcript: `c:\Users\rcataldi\AppData\Roaming\Code\User\workspaceStorage\74bb8480827fc856deba4cc19c1ef785\GitHub.copilot-chat\transcripts\5c4b3f6b-e7df-4122-baa2-a8a2cbe534c4.jsonl`
- Foundry docs:
  - https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agent-permissions
  - https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent
