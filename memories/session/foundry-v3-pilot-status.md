# Foundry V3 hosted-agents pilot — final status

## Outcome (achieved)

`inventory-health-check` is **active** in Foundry project `aipholidaris`:
- All 3 versions (v1, v2, v3) `status=active` after AcrPull granted to project MI.
- Visible alongside `ecommerce-catalog-search-fast` and `product-management-assortment-optimization-rich`.
- PR #1103 head: commit `5ea86ff3` (pushed; pre-push gate green).
- PR description updated with portal evidence and full fix matrix.

## What unblocked portal visibility

The decisive RBAC grant: **AcrPull on the project's system-assigned MI** (`2aff93dc-52e9-4773-ba75-6fedaa651c22`) at scope `holidaypeakhub405devacr`. Once granted, Foundry retried v1 and v2 in the background and they transitioned `failed` → `active`. v3 was provisioned cleanly under the corrected RBAC.

The previously-granted AcrPull on `instance_identity` (`e4512d94-…`) and `blueprint` (`d4f34fe8-…`) MIs were not the right principals — those are the agent's own identities for runtime model/tool access, not the registry-pull identity.

## Microsoft Learn doc reference

> "Container Registry Repository Reader for the project managed identity (image pulls)"
> "In the Azure portal, go to your Foundry project resource. Select Identity and copy the Object (principal) ID under System assigned."

Source: <https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent#configure-container-registry-permissions>

## Known follow-up (not blocking; tracked separately)

The deploy script (`scripts/ops/deploy_hosted_agent.py`) returns exit-1 even after Foundry transitions the version to `active` — the SDK's `create_version` response in the run that created v3 returned a stale `version=2 status=failed`, so the poll loop matched a previously-failed version. Fix candidates for a follow-up PR:
- Use the `versions` list endpoint to find the actually-newest version.
- Re-fetch the version via `get_version` immediately after `create_version` returns to avoid relying on the stale shape of the create-response.

The status normalization (`_normalize_status` in `lib/src/holiday_peak_lib/foundry_hosting/deploy.py`) is correct and tested — it converts `AgentVersionStatus.FAILED` → `failed`. The bug is upstream, in the version selection.

## Verification commands

```powershell
$tok = az account get-access-token --resource "https://ai.azure.com/" --query accessToken -o tsv
$h = @{ Authorization = "Bearer $tok"; "Foundry-Features" = "HostedAgents=V1Preview" }

# List all agents in the project
Invoke-WebRequest -Uri "https://holidaypeakhub405devais.services.ai.azure.com/api/projects/aipholidaris/agents?api-version=v1" -Headers $h |
  ForEach-Object Content | ConvertFrom-Json | ForEach-Object data |
  ForEach-Object { "{0}  kind={1}  v={2}  status={3}" -f $_.name, $_.versions.latest.definition.kind, $_.versions.latest.version, $_.versions.latest.status }
```

Expected output:
```
inventory-health-check  kind=hosted  v=3  status=active
ecommerce-catalog-search-fast  kind=prompt  v=35  status=active
product-management-assortment-optimization-rich  kind=prompt  v=6  status=active
```

## RBAC grants performed (idempotent — safe to re-run)

```powershell
$acrId = "/subscriptions/150e82e8-25db-4f1a-8e04-a2f6a77d26c4/resourceGroups/holidaypeakhub405-dev-rg/providers/Microsoft.ContainerRegistry/registries/holidaypeakhub405devacr"
# Decisive grant: project MI
az role assignment create --assignee-object-id 2aff93dc-52e9-4773-ba75-6fedaa651c22 --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId
# Defensive grants (kept; see runbook)
az role assignment create --assignee-object-id 351cdb70-0600-4c8c-b7f2-c6bf92ae1089 --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId  # Foundry account MI
az role assignment create --assignee-object-id e4512d94-6755-4fd1-97cf-60de45d176f3 --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId  # instance MI
az role assignment create --assignee-object-id d4f34fe8-ba6a-40c0-8b6f-117c6b758b4e --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId  # blueprint MI
```
