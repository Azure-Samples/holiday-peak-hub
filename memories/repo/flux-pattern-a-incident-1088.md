# Flux Pattern A takeover incident — issue #1088 / PR #1090 / fix PR #1091

## What happened
- PR #1090 (`058fe32b`) finalized Pattern A: `releases/crud` became sole source of truth for crud-service.
- Helm install caused a rolling update because rendered Deployment differed from live `azd deploy` spec (preflight init container was added).
- Fresh image pull broke: `mcr.microsoft.com/azure-cli:latest` is now Mariner, but chart's `postgres-auth-preflight` runs `apk add` (Alpine-only). Exit 127 → CrashLoopBackOff.
- Compounded: kustomize-controller pruned legacy ALB after Helm adoption (race), so external AGC routing died until ALB was re-applied from Helm-rendered manifest.

## Recovery actions (in order)
1. Manually stripped initContainers from live Deployment.
2. Suspended HelmRelease to prevent Helm reverting the strip.
3. Re-applied Helm-rendered manifest (`helm get manifest crud-service -n flux-system | kubectl apply -f -`) → ALB recreated.
4. PR #1091 (`ffcb500d`) flipped `preflight.postgresAuth.enabled: true → false` so chart values match reality.
5. Flux reconciled → Helm upgraded → HR Ready=True (UpgradeSucceeded). Manual suspend was wiped because git source has no `suspend: true`.

## Lessons learned
- **Pattern A is NOT no-op when chart values diverge from live.** `azd deploy`-applied Deployments may have drifted from chart defaults. Always diff `helm template` vs live Deployment before takeover.
- **Singular CRD name gotcha**: it's `applicationloadbalancer.alb.networking.azure.io` (singular), not plural. `kubectl get applicationloadbalancer -A` works; `applicationloadbalancers` errors NotFound.
- **Pruning shared resources is dangerous**: when migrating one service, kustomize-controller may prune resources that other services rely on (here: shared AGC ALB). Stagger or move shared resources out of any single service's tree first.
- **Init containers using base images you don't control are fragile**: `mcr.microsoft.com/azure-cli:latest` switched distros silently. Pin tags or write multi-distro install logic.
- **`BaseRepository.check_pool_health` self-recovers** (commit `811fdbe6`, PR #1087, fixes #911) — preflight gate is no longer load-bearing for pool init errors.

## Follow-ups (open)
- [ ] Chart fix: `apk`/`tdnf`/`apt-get` detection in preflight init or pin Alpine-tagged image.
- [ ] ADR-017 addendum: prune-vs-Helm-adopt race for Pattern A.
- [ ] Pre-flight checklist: `helm template` vs live `kubectl get deployment` diff before flipping a service to Pattern A.

## Verified post-fix state (2026-05-09 ~01:05 UTC)
- Flux GitRepository: `main@sha1:ffcb500d`
- Kustomization `holiday-peak-gitops-holiday-peak-crud`: Ready=True
- HelmRelease `crud-service` in `flux-system`: Ready=True (UpgradeSucceeded)
- Deployment: no initContainers, image `azd-deploy-1775825425`, 1 pod Ready
- AGC ALB: Programmed; Gateway+HTTPRoute all True
- External probes: CRUD `/health` 200, 26/26 agents `/<svc>/health` 200
