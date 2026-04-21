#!/usr/bin/env python3
"""Verify that the prompt baked into a built Docker image matches the repo.

This script is invoked as a CI gate immediately after a service image is
pushed to the registry and before any rollout. It refuses to proceed when
the in-image ``prompts/instructions.md`` diverges from the repo file that
produced the build, preventing prompt drift from ever reaching Foundry.

Usage:
    python scripts/ci/verify_image_prompt.py --service <service-name> \\
        --image-ref <registry/image@sha256:...>

Behaviour:
- When the repo has no prompt file for the service (e.g. ``crud-service``,
  ``ui``), the script prints a skip message and exits 0.
- When the prompt exists in the repo but is missing or different in the
  image, the script exits 1 with a clear comparison and remediation hint.
- Depends only on the Python stdlib and a local ``docker`` CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def service_to_package(service_name: str) -> str:
    """Convert a kebab-case service name to a snake_case package name."""
    return service_name.replace("-", "_")


def repo_prompt_path(service_name: str) -> Path:
    """Return the authoritative repo path for a service's prompt file."""
    package = service_to_package(service_name)
    return REPO_ROOT / "apps" / service_name / "src" / package / "prompts" / "instructions.md"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _run_in_image(image_ref: str, python_code: str) -> tuple[int, str, str]:
    """Run a Python one-liner inside the image and capture stdout/stderr."""
    cmd = [
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "python",
        image_ref,
        "-c",
        python_code,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _read_image_prompt(image_ref: str, package: str) -> tuple[str | None, str]:
    """Read the prompt text from inside the image.

    Returns (text, diagnostic). ``text`` is ``None`` when not found.
    """
    snippet = (
        "import sys\n"
        "from importlib.resources import files\n"
        f"pkg = {package!r}\n"
        "try:\n"
        "    res = files(pkg).joinpath('prompts/instructions.md')\n"
        "    sys.stdout.write(res.read_text(encoding='utf-8'))\n"
        "except ModuleNotFoundError:\n"
        "    sys.stderr.write(f'PACKAGE_NOT_FOUND:{pkg}')\n"
        "    sys.exit(2)\n"
        "except FileNotFoundError:\n"
        "    sys.stderr.write(f'PROMPT_NOT_FOUND:{pkg}/prompts/instructions.md')\n"
        "    sys.exit(3)\n"
    )
    rc, out, err = _run_in_image(image_ref, snippet)
    if rc == 0:
        return out, "ok"
    return None, f"exit={rc} stderr={err or 'n/a'}"


def verify(service_name: str, image_ref: str) -> int:
    repo_path = repo_prompt_path(service_name)

    if not repo_path.is_file():
        print(
            f"[verify_image_prompt] service={service_name}: "
            f"no repo prompt at {repo_path.relative_to(REPO_ROOT)} "
            "— no-prompt service, skipping."
        )
        return 0

    if not _docker_available():
        print(
            "[verify_image_prompt] ERROR: 'docker' CLI is not available on PATH. "
            "This gate must run on a Docker-enabled runner.",
            file=sys.stderr,
        )
        return 1

    repo_text = repo_path.read_text(encoding="utf-8")
    repo_sha = sha256_text(repo_text)

    package = service_to_package(service_name)
    image_text, diag = _read_image_prompt(image_ref, package)
    if image_text is None:
        print(
            "[verify_image_prompt] FAIL: prompt could not be read from image.\n"
            f"  service       : {service_name}\n"
            f"  package       : {package}\n"
            f"  image_ref     : {image_ref}\n"
            f"  repo_prompt   : {repo_path.relative_to(REPO_ROOT)}\n"
            f"  repo_sha256   : {repo_sha}\n"
            f"  diagnostic    : {diag}\n"
            "  hint          : ensure the service Dockerfile copies "
            "'apps/<svc>/src/<pkg>/prompts/instructions.md' into the package "
            "so 'importlib.resources' can locate it at runtime.",
            file=sys.stderr,
        )
        return 1

    image_sha = sha256_text(image_text)
    if image_sha != repo_sha:
        print(
            "[verify_image_prompt] FAIL: prompt sha256 divergence between repo and image.\n"
            f"  service       : {service_name}\n"
            f"  package       : {package}\n"
            f"  image_ref     : {image_ref}\n"
            f"  repo_prompt   : {repo_path.relative_to(REPO_ROOT)}\n"
            f"  repo_sha256   : {repo_sha}\n"
            f"  image_sha256  : {image_sha}\n"
            f"  repo_bytes    : {len(repo_text.encode('utf-8'))}\n"
            f"  image_bytes   : {len(image_text.encode('utf-8'))}\n"
            "  hint          : rebuild the image from the current commit and "
            "verify the Dockerfile copies the prompt file into the installed "
            "package directory (Track A2/A3 of the prompt-sync contract).",
            file=sys.stderr,
        )
        return 1

    print(
        f"[verify_image_prompt] OK service={service_name} package={package} "
        f"sha256={repo_sha} bytes={len(repo_text.encode('utf-8'))}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="Service name (kebab-case).")
    parser.add_argument(
        "--image-ref",
        required=True,
        help="Full image reference (registry/name@sha256:... or :tag).",
    )
    args = parser.parse_args()
    return verify(args.service, args.image_ref)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
