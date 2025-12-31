# Infra CLI quickstart

The CLI in this folder generates Dockerfiles and per-app Bicep modules from templates.

## Prerequisites
- Python 3.13+
- Azure CLI (`az`) if you plan to deploy
- Configure the CLI env once: from the repo root `bash .infra/config-cli.sh` (creates .infra/.venv and installs deps)

To reuse the env later: `source .infra/.venv/bin/activate`.

## Generate Bicep modules
- One app: `python .infra/cli.py generate-bicep --service <app>`
- All apps: `python .infra/cli.py generate-bicep --apply-all`
- Output: `.infra/modules/<app>/<app>.bicep` and `.infra/modules/<app>/<app>-main.bicep` rendered from templates in `.infra/templates/`

## Generate Dockerfiles
- One app: `python .infra/cli.py generate-dockerfile --service <app>`
- All apps: `python .infra/cli.py generate-dockerfile --apply-all`
- Output: `<repo>/apps/<app>/src/Dockerfile` rendered from `.infra/templates/Dockerfile.template`

## Deploy (optional)
- One app: `python .infra/cli.py deploy --service <app> --location <region> [--subscription-id <id>] [--resource-group <name>] [--app-image <image>]`
- All apps: `python .infra/cli.py deploy-all --location <region> [--subscription-id <id>] [--resource-group-prefix <prefix>] [--app-image <image>]`

Notes:
- The default image is `ghcr.io/OWNER/<app>:latest`; override with `--app-image`.
- Templates live in `.infra/templates/`; adjust them before regenerating output files.
