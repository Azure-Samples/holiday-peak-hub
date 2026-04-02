from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROOT_SECTION_PATTERN = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):\s*$")
_ENTRY_PATTERN = re.compile(r"^  (?P<key>[a-z0-9-]+):\s*$")


def parse_top_level_mapping_keys(file_path: Path, root_key: str) -> set[str]:
    """Return first-level mapping keys under a root section in a YAML file."""
    lines = file_path.read_text(encoding="utf-8").splitlines()
    in_root_section = False
    discovered_keys: set[str] = set()

    for line in lines:
        if not in_root_section:
            match = _ROOT_SECTION_PATTERN.match(line)
            if match and match.group("key") == root_key:
                in_root_section = True
            continue

        if re.match(r"^[^ \t#]", line):
            break

        entry_match = _ENTRY_PATTERN.match(line)
        if entry_match:
            discovered_keys.add(entry_match.group("key"))

    return discovered_keys


def validate_service_coverage(
    azure_config_path: Path,
    manifest_path: Path,
) -> tuple[list[str], list[str]]:
    """Return missing and extra service keys between azure.yaml and manifest."""
    azure_services = parse_top_level_mapping_keys(azure_config_path, "services")
    manifest_services = parse_top_level_mapping_keys(manifest_path, "services")

    if not azure_services:
        raise ValueError(f"No services discovered in {azure_config_path}")
    if not manifest_services:
        raise ValueError(f"No services discovered in {manifest_path}")

    missing_services = sorted(azure_services - manifest_services)
    extra_services = sorted(manifest_services - azure_services)

    return missing_services, extra_services


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that .infra/app-dependency-manifest.yaml contains an entry "
            "for every service declared in azure.yaml."
        )
    )
    parser.add_argument(
        "--azure-config",
        default="azure.yaml",
        type=Path,
        help="Path to azure.yaml service catalog.",
    )
    parser.add_argument(
        "--manifest",
        default=".infra/app-dependency-manifest.yaml",
        type=Path,
        help="Path to app dependency manifest file.",
    )

    args = parser.parse_args()

    missing_services, extra_services = validate_service_coverage(
        azure_config_path=args.azure_config,
        manifest_path=args.manifest,
    )

    if missing_services or extra_services:
        if missing_services:
            print(
                "Missing services in dependency manifest: "
                + ", ".join(missing_services),
                file=sys.stderr,
            )
        if extra_services:
            print(
                "Unknown services in dependency manifest: "
                + ", ".join(extra_services),
                file=sys.stderr,
            )
        return 1

    print("App dependency manifest covers all services declared in azure.yaml.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
