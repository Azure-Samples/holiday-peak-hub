# Tested-Image Promotion Model

This document describes the tested-image promotion pipeline used by the deploy workflows to ensure only validated code reaches AKS.

## Overview

The pipeline enforces a **build-once, deploy-immutable** model:

1. Code is merged to `main` and the `test` workflow runs (lint, unit tests, integration tests, contract checks).
2. On `test` success, `deploy-azd-dev` triggers automatically.
3. Each changed AKS service is built once per tested source SHA and pushed to ACR with a content-addressable digest.
4. Deploy jobs pull the immutable `repo@sha256:...` image reference from a build artifact and render Helm manifests that pin to that exact digest.
5. No image is ever rebuilt during deploy — the same tested artifact is promoted.

## Workflow Trigger Chain

```
push to main
  └─► test workflow (lint, test, contract)
        └─► on success: deploy-azd-dev (workflow_run trigger)
              └─► detect-changes → build-aks-images → deploy-crud / deploy-agents
```

## Image Build (build-aks-images job)

- Runs once per changed AKS service using a matrix strategy.
- Checks ACR for an existing image tagged with the source SHA; skips rebuild if found.
- Pushes the image to ACR and resolves its immutable `@sha256:` digest.
- Uploads the digest as a GitHub Actions artifact (`tested-image-<service>/image-ref.txt`).

## Image Deploy (deploy-crud / deploy-agents jobs)

- Downloads the `tested-image-<service>` artifact.
- Sets `SERVICE_<NAME>_IMAGE_NAME` to the immutable `repo@sha256:...` reference.
- Renders Helm via `render-helm.sh` and applies directly with `kubectl apply`.
- No `azd deploy --service` is used — manifests are applied directly for full control.

## Image-Only Deploys (skipProvision)

By default, auto-triggered deploys from `workflow_run` skip infrastructure provisioning (`skipProvision=true`). This means:

- `azd provision` is not called — existing infrastructure is reused.
- IaC validation steps (Event Hub declarations, dependency manifests) are skipped.
- Foundry model deployments are skipped unless infra files changed.
- APIM sync runs only for changed services (not forced).

To force full infrastructure reconciliation, use `workflow_dispatch` with `skipProvision=false`.

## ACR Access for GitHub-Hosted Runners

See [ACR Export-Policy Governance](acr-export-policy-governance.md) for details on how the pipeline handles locked-down ACR registries.

## Key Inputs

| Input | Default (auto) | Default (manual) | Purpose |
|-------|----------------|-------------------|---------|
| `skipProvision` | `true` | `false` | Skip `azd provision` for image-only deploys |
| `forceApimSync` | `false` | `true` | Force APIM API sync even without changed services |
| `autoAllowAcrRunnerIp` | `true` | `true` | Temporarily allow runner IP in ACR firewall |
| `serviceFilter` | (empty) | (empty) | Scope deploy to specific services |

## Rollback

To redeploy a previous tested image:

1. Use `workflow_dispatch` on `deploy-azd-dev`.
2. Set `testedSourceSha` to the commit SHA of the known-good build.
3. Leave `skipProvision=false` if unsure about infrastructure state.
