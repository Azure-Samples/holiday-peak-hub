from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
CORE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-azd.yml"
UI_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-ui-swa.yml"
UI_SWA_CONFIG_PATH = ROOT / "apps" / "ui" / "staticwebapp.config.json"
UI_PUBLIC_SWA_CONFIG_PATH = ROOT / "apps" / "ui" / "public" / "staticwebapp.config.json"
DEPLOY_MARKER = "      - name: Deploy UI to Azure Static Web Apps\n"
SMOKE_MARKER = "      - name: Smoke test UI host and API health after deploy\n"
SWA_ACTION = "        uses: Azure/static-web-apps-deploy@v1\n"
STANDALONE_PACKAGE_COMMANDS = [
    "app_build_command: >-",
    "yarn build &&",
    "mkdir -p .next/standalone/.next",
    "rm -rf .next/standalone/.next/static .next/standalone/public",
    "cp -R .next/static .next/standalone/.next/static",
    "cp -R public .next/standalone/public",
]


def _ui_deploy_block() -> str:
    content = UI_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert content.count(DEPLOY_MARKER) == 1
    return content.split(DEPLOY_MARKER, 1)[1].split(SMOKE_MARKER, 1)[0]


def _swa_action_blocks(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    blocks = []
    for block in content.split(SWA_ACTION)[1:]:
        blocks.append(block.split("\n      - name: ", 1)[0])
    return blocks


def _assert_standalone_packaging(block: str) -> None:
    for command in STANDALONE_PACKAGE_COMMANDS:
        assert command in block

    build = block.index("yarn build &&")
    cleanup = block.index("rm -rf .next/standalone/.next/static .next/standalone/public")
    copy_static = block.index("cp -R .next/static .next/standalone/.next/static")
    copy_public = block.index("cp -R public .next/standalone/public")

    assert build < cleanup < copy_static < copy_public


def test_swa_next_standalone_build_packages_static_and_public_assets() -> None:
    block = _ui_deploy_block()

    assert "app_location: apps/ui" in block
    assert "output_location: ''" in block
    _assert_standalone_packaging(block)


def test_reusable_deploy_workflow_swa_uploads_package_standalone_assets() -> None:
    blocks = _swa_action_blocks(CORE_WORKFLOW_PATH)
    assert len(blocks) == 2

    for block in blocks:
        assert "app_location: apps/ui" in block
        assert "output_location: ''" in block
        _assert_standalone_packaging(block)


def test_manual_prod_ui_deploy_rejects_source_overrides() -> None:
    content = UI_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "Manual prod UI deployments must use the workflow ref" in content
    assert (
        'if [ -n "${{ inputs.sourceSha }}" ] || [ -n "${{ inputs.sourceRef }}" ]; then' in content
    )
    assert "DEPLOY_SOURCE_CHECKOUT_REF" in content


def test_swa_hybrid_config_omits_navigation_fallback() -> None:
    root_config = json.loads(UI_SWA_CONFIG_PATH.read_text(encoding="utf-8"))
    public_config = json.loads(UI_PUBLIC_SWA_CONFIG_PATH.read_text(encoding="utf-8"))

    assert public_config == root_config
    assert "navigationFallback" not in root_config
    assert root_config["routes"] == [
        {
            "route": "/docs/*",
            "headers": {"cache-control": "public, max-age=600"},
        }
    ]
