# `azd up` fallback path

> **Audience.** Builders who want a turn-key deploy without using the public
> deploy-portal preview.
>
> **Owner.** Platform engineering team.

The deploy-portal at `/deploy/*` is the **opinionated, gated, audit-logged
preview path**. It runs against a single design-partner tenant and is not
yet GA. While it's in preview, the supported alternative is `azd up`.

This document is the canonical fallback that the
[`DeployPreviewBanner`](../../apps/ui/components/molecules/DeployPreviewBanner.tsx)
links to. The deploy-portal banner says, in essence: "If you want to do
this in your own subscription right now, run `azd up`." This page tells
you exactly how.

## TL;DR

```bash
git clone https://github.com/Azure-Samples/holiday-peak-hub.git
cd holiday-peak-hub
azd auth login
azd up
```

Total time end-to-end: ~25 min on a clean Azure subscription, depending on
region.

## Prerequisites

- Azure subscription with Owner or User Access Administrator on the
  resource group you'll use.
- [`azd`](https://aka.ms/azd-install) ≥ 1.10.
- [`docker`](https://docs.docker.com/get-docker/) (for building the
  container images locally if you don't pull from the Azure-Samples
  registry).
- [`yarn`](https://classic.yarnpkg.com/lang/en/docs/install/) ≥ 1.22 (for
  optionally running the UI locally).

## What `azd up` provisions

`azd up` runs the canonical Bicep templates in `infra/` and deploys the
full architecture — the same one defined in
[`docs/architecture/`](../architecture/). At a high level:

- AKS Automatic with managed AGC (Application Gateway for Containers).
- Cosmos DB for the warm-tier memory + connector cache.
- Redis for the hot tier.
- Blob Storage for the cold tier.
- Azure AI Foundry project for the SLM-first / LLM-fallback agent runtime.
- Container Apps for the agent services.
- Static Web Apps for the Next.js UI.
- Application Insights + Log Analytics for telemetry.

Region default: **westeurope**. Override with `azd env set AZURE_LOCATION
<region>` before `azd up`.

## What `azd up` does NOT do

- It does **not** run the deploy-portal pre-flight, rate-limit, or audit
  flow. Those are deploy-portal-specific.
- It does **not** wire up the OBO OAuth contract, because `azd up` runs
  with whatever credentials `azd auth login` provided.
- It does **not** run a third-party penetration test of your deployment.

If you want the gated, audited preview, use the deploy-portal at
`/deploy/configure` (design-partners only).

## Cleanup

```bash
azd down --purge
```

`azd down` removes every resource `azd up` provisioned. The `--purge` flag
also forces purge on Key Vault and Cognitive Services accounts so the
soft-delete window doesn't keep them around.

## Re-provisioning

`azd up` is idempotent. Running it again applies the latest templates
without re-provisioning resources that haven't changed.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Error: insufficient permissions` | Account missing Owner / UAA on RG | Grant the role at the RG scope and retry. |
| `Quota exceeded` | Subscription out of compute quota in the region | Switch region with `azd env set AZURE_LOCATION` or request quota. |
| Deployment succeeds but UI is empty | Bootstrap data not seeded yet | Wait ~5 min, or run `make seed` from the repo root. |
| `OperationNotAllowed: AKS preview not enabled` | AKS Automatic preview missing | `az feature register --name AKSAutomaticPreview --namespace Microsoft.ContainerService` then re-run. |

## Cross-references

- [Architecture overview](../architecture/README.md)
- [Deploy-portal OBO contract](../security/deploy-portal-obo.md)
- [Deploy-portal cleanup contract](../governance/deploy-portal-cleanup-contract.md)
- [`DeployPreviewBanner`](../../apps/ui/components/molecules/DeployPreviewBanner.tsx)
