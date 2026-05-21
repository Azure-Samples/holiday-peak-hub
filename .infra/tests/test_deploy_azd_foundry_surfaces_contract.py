"""Contract tests for Foundry surface deployment automation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-azd.yml"
DEV_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-azd-dev.yml"
JOB_MARKER = "  deploy-foundry-surfaces:\n"
RESTORE_ACR_MARKER = "  restore-acr-build-access:\n"


def _core_workflow() -> str:
    return CORE_WORKFLOW_PATH.read_text(encoding="utf-8")


def _dev_workflow() -> str:
    return DEV_WORKFLOW_PATH.read_text(encoding="utf-8")


def _foundry_surface_job() -> str:
    content = _core_workflow()
    assert content.count(JOB_MARKER) == 1
    return content.split(JOB_MARKER, 1)[1].split(RESTORE_ACR_MARKER, 1)[0]


def test_reusable_workflow_exposes_explicit_foundry_surface_controls() -> None:
    workflow = _core_workflow()

    assert "deployFoundrySurfaces:" in workflow
    assert "foundrySurfaceMode:" in workflow
    assert "default: false" in workflow
    assert "default: plan" in workflow


def test_dev_entrypoint_plans_surfaces_by_default_but_apply_is_explicit() -> None:
    workflow = _dev_workflow()

    assert "deployFoundrySurfaces:" in workflow
    assert "default: true" in workflow
    assert "foundrySurfaceMode:" in workflow
    assert "options:" in workflow
    assert "- plan" in workflow
    assert "- apply" in workflow
    assert "foundrySurfaceMode: ${{ github.event_name == 'workflow_dispatch'" in workflow


def test_foundry_surface_job_uses_tested_images_and_oidc() -> None:
    job = _foundry_surface_job()

    assert "needs.detect-changes.outputs.changed_agent_services_csv != ''" in job
    assert "- prepare-acr-build-access" in job
    assert "- build-aks-images" in job
    assert "azure/login@v2" in job
    assert "actions/download-artifact@v4" in job
    assert "pattern: tested-image-*" in job
    assert "foundry-image-map.json" in job
    assert "scripts/ops/register_foundry_surfaces.py" in job
    assert "--image-map-file" in job
    assert "--services \"${{ needs.detect-changes.outputs.changed_agent_services_csv }}\"" in job
    assert "actions/upload-artifact@v4" in job
    assert "foundry-surface-plan-${{ inputs.environment }}" in job


def test_foundry_surface_job_requires_plan_or_apply_and_preserves_aks_runtime() -> None:
    job = _foundry_surface_job()

    assert "foundrySurfaceMode must be 'plan' or 'apply'." in job
    assert "MODEL_DEPLOYMENT_NAME_FAST: gpt-5-nano" in job
    assert "MODEL_DEPLOYMENT_NAME_RICH: gpt-5" in job
    assert "APIM_BASE_URL: ${{ needs.provision.outputs.APIM_GATEWAY_URL }}" in job
    assert "PROJECT_ENDPOINT: ${{ needs.provision.outputs.PROJECT_ENDPOINT }}" in job
    assert "Run in plan mode, then update the ACR network policy intentionally before apply." in job
    assert "az aks" not in job
    assert "kubectl" not in job
    assert "assistants" not in job.lower()
    assert "PromptAgentDefinition" not in job


def test_foundry_surface_job_runs_before_acr_state_restoration() -> None:
    workflow = _core_workflow()

    assert workflow.index(JOB_MARKER) < workflow.index(RESTORE_ACR_MARKER)