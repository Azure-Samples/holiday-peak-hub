# AKS dev cluster auto-stop recovery runbook

## Symptom

`kubectl` DNS fails with `lookup holidaypeakhub405-dev-aks-*.hcp.centralus.azmk8s.io: no such host` and several deployments show `READY 0/2, UP-TO-DATE 0`.

## Root cause

The dev AKS cluster `holidaypeakhub405-dev-aks` is auto-stopped overnight for cost. When it restarts, two known issues block agent pods from coming back:

1. **AKS API server DNS goes away** while the cluster is in `Stopped` state. `az aks list` shows `Stopped`, and the API server FQDN doesn't resolve.
2. **`azure-wi-webhook-webhook-service`** (Azure Workload Identity admission webhook) endpoints are sometimes empty for the first few minutes after restart. Any Deployment whose pods carry the workload-identity label gets `ReplicaFailure: FailedCreate` with `failed calling webhook "mutation.azure-workload-identity.io"` because the service has no endpoints.

The replicaset-controller does NOT auto-retry once the webhook recovers — the deployment stays at `UP-TO-DATE: 0` forever. A `kubectl rollout restart` is required to kick a new RS creation cycle.

## Recovery (verified 2026-05-12)

```powershell
# 1. Confirm cluster state
az aks list --query "[].{name:name,state:powerState.code}" -o table

# 2. Start cluster if Stopped (takes ~8 min)
az aks start --name holidaypeakhub405-dev-aks --resource-group holidaypeakhub405-dev-rg
# wait until provisioningState == "Succeeded"

# 3. Refresh kubeconfig
$env:KUBECONFIG="$env:TEMP\holiday-peak-kubeconfig"
az aks get-credentials --name holidaypeakhub405-dev-aks --resource-group holidaypeakhub405-dev-rg `
  --overwrite-existing --file $env:KUBECONFIG
kubelogin convert-kubeconfig -l azurecli --kubeconfig $env:KUBECONFIG

# 4. Find deployments stuck at UP-TO-DATE: 0
kubectl -n holiday-peak-agents get deploy

# 5. Confirm webhook is back (endpoints non-empty)
kubectl -n kube-system get endpoints azure-wi-webhook-webhook-service

# 6. Rollout-restart any stuck deployments
kubectl -n holiday-peak-agents rollout restart deploy/<name>
```

## Affected services on the 2026-05-12 incident

Needed rollout restart:
- ecommerce-checkout-support
- ecommerce-order-status
- logistics-carrier-selection
- logistics-returns-support
- logistics-route-issue-detection
- truth-enrichment
- truth-hitl
- truth-ingestion

After restart all 26 reached ≥1 Ready replica. A few (eta-computation, checkout-support, order-status, carrier-selection) stay at 1/2 because the startup probe is tight and racy against telemetry init — pods cycle through 2-3 restarts before stabilizing.

## Known startup-probe flake (separate follow-up)

One replica of each of {logistics-eta-computation, ecommerce-checkout-support, ecommerce-order-status, logistics-carrier-selection} stays in CrashLoopBackOff while the other serves traffic. Logs show `Uvicorn running on http://0.0.0.0:8000` and `Overriding of current TracerProvider is not allowed` (telemetry init race) but no `Application startup complete`. The startup probe times out before the slow worker finishes binding. Fix candidates:
- Increase startup probe `failureThreshold` / `initialDelaySeconds` in the Helm chart for these services.
- Use single-worker uvicorn (`--workers 1`) to avoid the TracerProvider override race.
- Wrap the unconditional `from azure.monitor.opentelemetry import configure_azure_monitor` at `lib/src/holiday_peak_lib/utils/telemetry.py:34` in try/except + pin `opentelemetry-sdk<1.30` in `lib/src/pyproject.toml`.
