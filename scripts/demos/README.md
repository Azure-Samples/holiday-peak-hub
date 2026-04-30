# Demo Scripts

Quick-start runnable scripts for exercising all 26 agent services and the CRUD service.

## Contents

| Script | Platform | Description |
|--------|----------|-------------|
| [`curl-examples.sh`](curl-examples.sh) | Bash (Linux/macOS/WSL) | curl calls for all 26 agents + CRUD |
| [`powershell-examples.ps1`](powershell-examples.ps1) | PowerShell (Windows) | Invoke-RestMethod calls for all services |

## Prerequisites

1. Services running locally (ports 8000–8026) **or** reachable via APIM gateway.
2. Data seeded — use one of:
   - **Curated catalog**: `python -m crud_service.scripts.seed_demo_data` (100 products)
   - **Kaggle Olist dataset**: `python scripts/ops/load-kaggle-olist-dataset.py --download --crud-url http://localhost:8000`

## Usage

### Bash
```bash
export BASE_URL=http://localhost   # or your APIM gateway URL
bash scripts/demos/curl-examples.sh
```

### PowerShell
```powershell
$env:BASE_URL = "http://localhost"
.\scripts\demos\powershell-examples.ps1
```

## Related Documentation

- [Demo Guide](../../docs/demos/README.md) — full demo index with interactive scenarios
- [API Examples README](../../docs/demos/api-examples/README.md) — API reference and Postman collection
- [Ops Scripts](../ops/) — data loading, preflight checks, provisioning
