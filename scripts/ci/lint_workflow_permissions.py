"""Static linter for reusable-workflow permission-cap violations.

GitHub Actions enforces a hard rule on nested ``workflow_call`` chains:

    Permissions can only be MAINTAINED or REDUCED — not elevated —
    throughout the chain.

If a callee job declares ``permissions:`` keys that the caller did not grant
to its ``uses:`` job, the GitHub orchestrator rejects the run at startup
with ``startup_failure`` BEFORE any runner is allocated.  This failure mode
is invisible to ``actionlint`` and ``yaml.safe_load`` because it requires
correlating multiple files.

This script:

1.  Discovers every workflow under ``.github/workflows/``.
2.  Builds a map ``callee_path -> set(permission_keys)`` for callees with
    declared permissions on any job.
3.  For every caller that uses a local callee
    (``uses: ./.github/workflows/<file>.yml``), checks that the per-job
    ``permissions:`` grant on the caller's ``uses:`` job is a SUPERSET of
    the union of the callee's declared per-job permissions.
4.  Reports violations and exits non-zero.

Why a custom linter:

* ``actionlint`` validates syntax and per-file semantics, not cross-file
  permission caps.
* GitHub's runtime check catches the violation only AFTER the workflow has
  been dispatched, causing silent ``startup_failure`` storms.
* The PR ``ee9f6206`` (#1097) regression sat undetected for ~2 days
  because the only signal was a 7-second "startup_failure" run with no
  logs.  A static check at PR time would have rejected it immediately.

Run via:

    python scripts/ci/lint_workflow_permissions.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import yaml

WORKFLOWS_DIR = Path(".github/workflows")

# Permission keys recognized by GitHub Actions.  Source:
# https://docs.github.com/en/actions/security-guides/automatic-token-authentication
_KNOWN_PERMISSION_KEYS: Set[str] = {
    "actions",
    "attestations",
    "checks",
    "contents",
    "deployments",
    "discussions",
    "id-token",
    "issues",
    "models",
    "packages",
    "pages",
    "pull-requests",
    "repository-projects",
    "security-events",
    "statuses",
}

_WRITE_LEVELS: Set[str] = {"write"}


def _load_workflow(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _normalize_permissions(value) -> Dict[str, str]:
    """Return a mapping of permission_key -> level.

    Accepts the two forms GitHub Actions allows:

    * ``permissions: read-all`` (string shorthand) — treated as read on all keys
    * ``permissions: write-all`` (string shorthand) — treated as write on all keys
    * ``permissions: { key: level, ... }`` (explicit mapping) — used as-is
    """

    if value is None:
        return {}
    if isinstance(value, str):
        if value == "read-all":
            return {k: "read" for k in _KNOWN_PERMISSION_KEYS}
        if value == "write-all":
            return {k: "write" for k in _KNOWN_PERMISSION_KEYS}
        if value == "{}":
            return {}
        return {}
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    return {}


def _is_local_callee(uses: str) -> bool:
    return isinstance(uses, str) and uses.startswith("./.github/workflows/")


def _callee_relative_path(uses: str) -> Path:
    # `uses: ./.github/workflows/foo.yml` -> repo-relative Path
    # NB: ``str.lstrip("./")`` strips *characters*, not a prefix — strip the
    # exact leading ``./`` once.
    cleaned = uses[2:] if uses.startswith("./") else uses
    return Path(cleaned)


def _collect_callee_required_permissions(callee_doc: dict) -> Dict[str, str]:
    """Union of effective per-job permissions in the callee.

    GitHub Actions resolves a job's effective ``permissions:`` as:

    * if the job declares its own ``permissions:`` map, that map applies;
    * otherwise the workflow-level ``permissions:`` map applies.

    The cap rule for nested-workflow calls operates on those EFFECTIVE
    permissions, not just on ones that happen to be redeclared on the job.
    A linter that ignores the workflow-level fallback will miss the case
    where every job inherits the workflow-level grant — e.g. the
    ``deploy-azd-truth.yml`` scoped entrypoint, where the callee
    ``deploy-azd.yml`` declares workflow-level ``contents: write`` and
    most jobs inherit it.
    """

    workflow_perms = _normalize_permissions(callee_doc.get("permissions"))
    required: Dict[str, str] = dict(workflow_perms)
    jobs = callee_doc.get("jobs", {}) or {}
    for _job_id, job_def in jobs.items():
        if not isinstance(job_def, dict):
            continue
        job_perms = _normalize_permissions(job_def.get("permissions"))
        # Effective permissions for the job = job-level if present else workflow-level.
        effective = job_perms if job_perms else workflow_perms
        for key, level in effective.items():
            existing = required.get(key)
            # Escalate the "needed" level if any job wants write.
            if existing is None or (level in _WRITE_LEVELS and existing not in _WRITE_LEVELS):
                required[key] = level
    return required


def _violations_for_call(
    caller_path: Path,
    caller_job_id: str,
    caller_permissions: Dict[str, str],
    callee_path: Path,
    callee_required: Dict[str, str],
) -> List[str]:
    out: List[str] = []
    for key, needed_level in callee_required.items():
        granted = caller_permissions.get(key)
        if needed_level in _WRITE_LEVELS:
            if granted not in _WRITE_LEVELS:
                out.append(
                    (
                        f"{caller_path.as_posix()}::{caller_job_id} grants "
                        f"'{key}: {granted or '<absent>'}' but callee "
                        f"{callee_path.as_posix()} requires '{key}: write'. "
                        "GitHub will reject with startup_failure."
                    )
                )
        else:
            if granted is None:
                out.append(
                    (
                        f"{caller_path.as_posix()}::{caller_job_id} does not grant "
                        f"'{key}' but callee {callee_path.as_posix()} requires "
                        f"'{key}: {needed_level}'. GitHub will reject with "
                        "startup_failure."
                    )
                )
    return out


def _iter_workflows() -> Iterable[Path]:
    for path in sorted(WORKFLOWS_DIR.rglob("*.yml")):
        yield path
    for path in sorted(WORKFLOWS_DIR.rglob("*.yaml")):
        yield path


def main() -> int:
    if not WORKFLOWS_DIR.is_dir():
        print(f"workflow directory not found: {WORKFLOWS_DIR}", file=sys.stderr)
        return 2

    # First pass: cache callee permission requirements.
    callee_required: Dict[Path, Dict[str, str]] = {}
    for path in _iter_workflows():
        try:
            doc = _load_workflow(path)
        except yaml.YAMLError as exc:
            print(f"::error file={path}::YAML parse error: {exc}")
            return 2
        triggers = doc.get(True) or doc.get("on") or {}
        # In safe_load, the bare key ``on`` becomes Python ``True``.  Handle both.
        if isinstance(triggers, dict) and "workflow_call" in triggers:
            callee_required[path] = _collect_callee_required_permissions(doc)

    # Second pass: walk callers and validate.
    violations: List[Tuple[Path, str]] = []
    for caller_path in _iter_workflows():
        try:
            caller_doc = _load_workflow(caller_path)
        except yaml.YAMLError:
            continue
        # Workflow-level ``permissions:`` is the fallback when a job omits its
        # own ``permissions:``.  ``actions/runner`` resolves this before
        # validating callee caps, so the linter must mirror that semantics.
        caller_workflow_perms = _normalize_permissions(caller_doc.get("permissions"))
        jobs = caller_doc.get("jobs", {}) or {}
        for job_id, job_def in jobs.items():
            if not isinstance(job_def, dict):
                continue
            uses = job_def.get("uses")
            if not _is_local_callee(uses):
                continue
            callee_path = _callee_relative_path(uses)
            required = callee_required.get(callee_path)
            if not required:
                # callee has no per-job permission declarations -> nothing to check
                continue
            caller_perms = _normalize_permissions(job_def.get("permissions"))
            if not caller_perms:
                caller_perms = dict(caller_workflow_perms)
            for msg in _violations_for_call(
                caller_path, str(job_id), caller_perms, callee_path, required
            ):
                violations.append((caller_path, msg))

    if violations:
        print("Workflow permission-cap violations detected:\n", file=sys.stderr)
        for _path, msg in violations:
            print(f"::error::{msg}", file=sys.stderr)
        print(
            "\nFix: grant the missing permission on the caller's `jobs.<id>.permissions` map, "
            "or remove the requirement from the callee. See ADR-017 and "
            "https://docs.github.com/en/actions/using-workflows/reusing-workflows"
            "#access-and-permissions-for-nested-workflows",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(callee_required)} callee workflow(s) checked, no permission-cap violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
