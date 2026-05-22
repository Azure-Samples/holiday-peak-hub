from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-ui-swa.yml"
DEPLOY_MARKER = "      - name: Deploy UI to Azure Static Web Apps\n"
SMOKE_MARKER = "      - name: Smoke test UI host and API health after deploy\n"


def _deploy_block() -> str:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert content.count(DEPLOY_MARKER) == 1
    return content.split(DEPLOY_MARKER, 1)[1].split(SMOKE_MARKER, 1)[0]


def test_swa_next_standalone_build_packages_static_and_public_assets() -> None:
    block = _deploy_block()

    assert "app_location: apps/ui" in block
    assert "output_location: ''" in block
    assert "app_build_command: >-" in block
    assert "yarn build &&" in block
    assert "mkdir -p .next/standalone/.next" in block
    assert "rm -rf .next/standalone/.next/static .next/standalone/public" in block
    assert "cp -R .next/static .next/standalone/.next/static" in block
    assert "cp -R public .next/standalone/public" in block

    build = block.index("yarn build &&")
    cleanup = block.index("rm -rf .next/standalone/.next/static .next/standalone/public")
    copy_static = block.index("cp -R .next/static .next/standalone/.next/static")
    copy_public = block.index("cp -R public .next/standalone/public")

    assert build < cleanup < copy_static < copy_public
