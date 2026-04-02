import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import validate_app_dependency_manifest as validator


def test_parse_top_level_mapping_keys_ignores_non_service_sections(tmp_path) -> None:
    config = tmp_path / "azure.yaml"
    config.write_text(
        """
services:
  ui:
    host: staticwebapp
  crud-service:
    host: aks
hooks:
  preprovision:
    windows:
      shell: pwsh
""".strip(),
        encoding="utf-8",
    )

    discovered = validator.parse_top_level_mapping_keys(config, "services")

    assert discovered == {"ui", "crud-service"}


def test_validate_service_coverage_reports_missing_and_extra(tmp_path) -> None:
    azure_config = tmp_path / "azure.yaml"
    azure_config.write_text(
        """
services:
  ui:
    host: staticwebapp
  crm-support-assistance:
    host: aks
""".strip(),
        encoding="utf-8",
    )

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
services:
  ui:
    host: staticwebapp
  unexpected-service:
    host: aks
""".strip(),
        encoding="utf-8",
    )

    missing, extra = validator.validate_service_coverage(azure_config, manifest)

    assert missing == ["crm-support-assistance"]
    assert extra == ["unexpected-service"]


def test_validate_service_coverage_passes_when_manifest_is_aligned(tmp_path) -> None:
    azure_config = tmp_path / "azure.yaml"
    azure_config.write_text(
        """
services:
  ui:
    host: staticwebapp
  truth-hitl:
    host: aks
""".strip(),
        encoding="utf-8",
    )

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
services:
  ui:
    host: staticwebapp
  truth-hitl:
    host: aks
""".strip(),
        encoding="utf-8",
    )

    missing, extra = validator.validate_service_coverage(azure_config, manifest)

    assert missing == []
    assert extra == []
