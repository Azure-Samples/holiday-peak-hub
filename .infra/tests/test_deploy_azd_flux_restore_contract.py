from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-azd.yml"
RESTORE_JOB_MARKER = "  restore-flux-source-default-branch:\n"


def _restore_flux_job() -> str:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert content.count(RESTORE_JOB_MARKER) == 1
    return content.split(RESTORE_JOB_MARKER, 1)[1]


def test_flux_restore_falls_back_to_aks_command_invoke_when_direct_kubectl_fails() -> None:
    job = _restore_flux_job()

    assert "restore_flux_source() {" in job
    assert "if ! restore_flux_source; then" in job
    assert "Direct kubectl Flux restore failed; retrying through az aks command invoke." in job
    assert "REMOTE_COMMAND=$(cat <<EOF" in job
    assert "az aks command invoke" in job
    assert '--command "$REMOTE_COMMAND"' in job

    direct_restore = job.index("restore_flux_source() {")
    fallback = job.index("az aks command invoke")
    optional_reconcile = job.index('flux reconcile source git "$FLUX_SOURCE"')

    assert direct_restore < fallback < optional_reconcile