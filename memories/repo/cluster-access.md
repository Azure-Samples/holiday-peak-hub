# Live cluster + Azure access in this workspace

When working in `holiday-peak-hub`, runtime cluster access exists. Don't assume it's gated.

## Available access

- Azure subscription: `MCAPS-Hybrid-REQ-67664-2023-rcataldi` (id `150e82e8-25db-4f1a-8e04-a2f6a77d26c4`).
  - User: `rcataldi@microsoft.com`.
  - `az account show` returns successfully — no need to re-authenticate.
- AKS cluster `holidaypeakhub405-dev-aks` (resource group `holidaypeakhub405-dev-rg`, region `centralus`, k8s v1.34.6, Running).
- Second AKS cluster `hph711poc-poc-aks` (`hph711poc-poc` RG, eastus2) is Stopped.
- `kubectl` context defaults to `holidaypeakhub405-dev-aks`. Switch with `kubectl config use-context hph711poc-poc-aks` if needed.

## Useful in-cluster diagnostics

- Pod containers do NOT have `curl`. Use `kubectl exec ... -- python -c "..."` for HTTP probes.
- `urllib.error.HTTPError.read()` returns the response body even on non-2xx responses.
- Postgres `holidaypeakhub405-dev-postgres` has public networking DISABLED — the firewall-rule API errors out, but the DB is reachable from in-cluster pods because they share the AKS VNet path. Don't waste time on firewall tooling.
- Postgres auth mode = `entra`. `DefaultAzureCredential.get_token('https://ossrdbms-aad.database.windows.net/.default')` returns a 1980-byte token within seconds when run from a CRUD pod with the workload identity.
- The CRUD identity is `holidaypeakhub405-dev-crud-identity` (clientId `b09349cf-547f-409f-8b96-f3288ddedf34`) — exposed as `AZURE_CLIENT_ID` env var in the pod.

## Flux state on `holidaypeakhub405-dev-aks`

- `holiday-peak-gitops` GitRepository tracks `Azure-Samples/holiday-peak-hub` (ADR-033 Phase B).
- Two Kustomizations: `holiday-peak-gitops-holiday-peak-crud` (path `.kubernetes/rendered/crud`) and `holiday-peak-gitops-holiday-peak-agents` (depends on the crud Kustomization).
- Reconciliation timeout = `10m0s`, `Wait: true` — health-check failures cause `HealthCheckFailed` events but the Kustomization keeps retrying.
- HelmReleases: `ecommerce-catalog-search`, `truth-enrichment`, `truth-hitl` (all live as of May 9, 2026).

## What this enables

When triaging issues that say "needs runtime cluster access", I should actually go look at `kubectl get pods/events/logs`, `az` CLI, and live-reproduce in pods before declaring the issue blocked. Past examples where this matters: #911, #927.
