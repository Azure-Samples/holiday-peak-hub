# Scripts

All automation scripts for Holiday Peak Hub, organized by language and purpose.

---

## Structure

```
scripts/
├── python/
│   ├── ci/       CI validation gates (run in GitHub Actions)
│   └── ops/      Operational scripts (data loading, audits, checks)
├── powershell/
│   ├── ops/      Operational scripts (provisioning, recovery, validation)
│   └── demos/    Demo runner scripts
├── shell/
│   ├── ops/      Operational bash scripts (reconciliation, watchdogs)
│   └── demos/    Demo runner scripts (curl examples)
└── RECONCILE-POSTGRES.md
```

---

## Python (`scripts/python/`)

### CI Gates (`python/ci/`)

| Script | Purpose |
|--------|---------|
| `regen_service_deploy_entrypoints.py` | Regenerate per-service deploy-azd entrypoint workflows |
| `validate_k8s_name_length.py` | Ensure Kubernetes resource names stay within 63-char limit |
| `validate_swa_hybrid_contract.py` | Validate SWA hybrid runtime contract compatibility |
| `verify_dockerfile_prompts.py` | Verify all agent Dockerfiles copy the prompts directory |
| `verify_foundry_prompt.py` | Verify Foundry agent instructions match repo prompts |
| `verify_image_prompt.py` | Verify prompt SHA256 match between repo and built image |

### Ops (`python/ops/`)

| Script | Purpose |
|--------|---------|
| `audit_main_governance.py` | Audit PR-only protections on `main` branch |
| `check_event_schema_contracts.py` | Validate canonical event schema compatibility |
| `check_markdown_links.py` | Fail on unresolved internal Markdown links |
| `check_prompt_agent_consistency.py` | Enforce prompt-to-agent governance consistency |
| `load-kaggle-olist-dataset.py` | Download + transform Kaggle Olist ecommerce data → CRUD API |
| `pre_push_gate.py` | Local push gate (mirrors CI lint/test) |
| `seed_hitl_queue.py` | Seed the HITL review Event Hub queue for demos |

---

## PowerShell (`scripts/powershell/`)

### Ops (`powershell/ops/`)

| Script | Purpose |
|--------|---------|
| `agc-bisect.ps1` | Bisect AGC (Application Gateway for Containers) issues |
| `crud-post-write-check.ps1` | Validate CRUD liveness and write paths via HTTP |
| `demo-deprovision.ps1` | Tear down demo environment |
| `demo-preflight-validate.ps1` | Pre-demo infrastructure readiness check |
| `demo-provision.ps1` | Provision demo environment (azd up) |
| `demo-recover-and-seed.ps1` | Recover from nightly shutdown + seed data |
| `reconcile-postgres-password.ps1` | Reconcile PostgreSQL admin password with Key Vault |
| `start-dev-environment.ps1` | Start stopped dev resources (PostgreSQL, AKS) |

### Demos (`powershell/demos/`)

| Script | Purpose |
|--------|---------|
| `powershell-examples.ps1` | Invoke-RestMethod calls for all 26 agents + CRUD |

---

## Shell/Bash (`scripts/shell/`)

### Ops (`shell/ops/`)

| Script | Purpose |
|--------|---------|
| `agc-bisect.sh` | Bisect AGC issues (bash equivalent) |
| `reconcile-postgres-password.sh` | Reconcile PostgreSQL admin password (bash equivalent) |
| `watchdog-apim-agc-swa-drift.sh` | Watchdog for APIM/AGC/SWA configuration drift |

### Demos (`shell/demos/`)

| Script | Purpose |
|--------|---------|
| `curl-examples.sh` | curl calls for all 26 agents + CRUD |

---

## Related Documentation

- [Demo Guide](../docs/demos/README.md) — interactive scenarios and demo index
- [RECONCILE-POSTGRES.md](RECONCILE-POSTGRES.md) — PostgreSQL password reconciliation procedure
- [Standalone Deployment Guide](../docs/architecture/standalone-deployment-guide.md) — CI enforcement scripts
- [Governance](../docs/governance/README.md) — drift detection and audit scripts
