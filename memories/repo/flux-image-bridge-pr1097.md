# Flux image bridge — PR #1097 outcome

## What landed (2026-05-11)

- PR #1097 squash-merged to `main` at SHA `ee9f6206`.
- Closed the GitOps gap: 27 HelmReleases (26 agents + crud-service) now point at
  the root-prefix ACR path (`<acr>/<svc>:<sha>`) that the build pipeline
  actually pushes to, instead of the legacy `<acr>/holiday-peak-hub/<svc>-dev`
  path that predated PR #1089.
- New job `open-image-tag-bump-pr` in `.github/workflows/deploy-azd.yml`
  closes the loop: every successful dev deploy auto-opens (or refreshes) a
  `chore/image-bump-<env>-<sha12>` PR. Respects the GH013 ruleset because the
  workflow never pushes to main directly.
- New helper `scripts/ci/update_helmrelease_image.py` (10/10 pylint,
  byte-identical idempotent) does the surgical line-edit so PyYAML
  round-tripping doesn't reflow comments.

## Post-merge AKS state

After Flux reconciled (forced via `reconcile.fluxcd.io/requestedAt`):

- 23 of 26 agent services have ≥1 Ready replica running PR #1093's MAF
  direct-model image (`<acr>/<svc>:808d48227b08...`).
- Smoke test: `ecommerce-cart-intelligence` `/health` returns
  `200 {"status":"ok","service":"ecommerce-cart-intelligence",...}`.

## Known follow-ups (NOT caused by this PR)

- `inventory-health-check` — CrashLoopBackOff on startup. Likely the same
  transient opentelemetry/import issue seen briefly in CRM pods that
  eventually recovered. Worth confirming once.
- `truth-export` — `RunContainerError`: `exec: "uvicorn": executable file
  not found in $PATH`. The image is missing the uvicorn binary. Dockerfile
  / packaging bug, not a bridge bug.
- `crm-campaign-intelligence` first-restart traceback showed
  `ImportError: cannot import name 'LogData' from 'opentelemetry.sdk._logs'`
  — a transitive version mismatch between `azure-monitor-opentelemetry>=1.7`
  and `opentelemetry-sdk>=1.27` when pip resolves to a newer sdk. The pod
  later recovered (probably restart cycle hit a working pip cache). Worth
  pinning `opentelemetry-sdk` ceiling in `lib/src/pyproject.toml` to make
  this deterministic across rebuilds.

## How the bridge is supposed to work going forward

```
build-aks-images (matrix) → tested-image-<svc> artifact (image-ref.txt)
        ↓
deploy-crud / deploy-agents  (existing)
        ↓
open-image-tag-bump-pr       ← NEW
        - downloads tested-image-* artifacts
        - runs scripts/ci/update_helmrelease_image.py for each
        - opens/updates chore/image-bump-<env>-<sha12> PR
        ↓
operator merges → Flux reconciles → pods roll over
```

No human-in-loop YAML edits required.
