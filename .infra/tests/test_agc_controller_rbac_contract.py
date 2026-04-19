from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BICEP_PATH = ROOT / ".infra" / "modules" / "shared-infrastructure" / "shared-infrastructure.bicep"
BASH_HOOK_PATH = ROOT / ".infra" / "azd" / "hooks" / "ensure-agc-controller.sh"
POWERSHELL_HOOK_PATH = ROOT / ".infra" / "azd" / "hooks" / "ensure-agc-controller.ps1"


def test_shared_infrastructure_declares_day_zero_agc_controller_role_assignments() -> None:
    bicep = BICEP_PATH.read_text(encoding="utf-8")

    assert "resource agcControllerReaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01'" in bicep
    assert "resource agcControllerAgcConfigManagerRole 'Microsoft.Authorization/roleAssignments@2022-04-01'" in bicep
    assert "resource agcControllerSubnetNetworkContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01'" in bicep
    assert "scope: aksNodeResourceGroupScope" in bicep
    assert "scope: agcSubnetResource" in bicep
    assert "acdd72a7-3385-48ef-bd42-f606fba81ae7" in bicep
    assert "fbc52c3f-28ad-4303-a892-8a056630b8f1" in bicep
    assert "4d97b98b-1d4f-4787-a291-c67834d212e7" in bicep


def test_agc_controller_hooks_verify_rbac_prerequisites_without_mutating_role_assignments() -> None:
    bash_hook = BASH_HOOK_PATH.read_text(encoding="utf-8")
    powershell_hook = POWERSHELL_HOOK_PATH.read_text(encoding="utf-8")

    assert "require_role_assignment" in bash_hook
    assert "az role assignment list --assignee-object-id" in bash_hook
    assert "az role assignment create" not in bash_hook
    assert "Validated AGC controller RBAC prerequisites." in bash_hook
    assert "Re-run shared infrastructure provisioning before installing the ALB controller." in bash_hook

    assert "Require-RoleAssignment" in powershell_hook
    assert "az role assignment list --assignee-object-id" in powershell_hook
    assert "az role assignment create" not in powershell_hook
    assert "Validated AGC controller RBAC prerequisites." in powershell_hook
    assert "Re-run shared infrastructure provisioning before installing the ALB controller." in powershell_hook