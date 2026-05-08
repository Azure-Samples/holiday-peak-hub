"""Audit repository documentation for incongruences against canonical positioning.

This script enforces alignment between authored markdown files and the canonical
positioning declared in ``.github/instructions/repository-purpose.instructions.md``.
It is run weekly (see ``.github/workflows/docs-consistency-audit.yml``) and on
manual dispatch.

The audit is **non-destructive**. It detects drift and emits a structured report
(JSON + human-readable Markdown). When invoked from the workflow, the report is
attached to a GitHub issue tagged ``documentation, drift`` so the
ContentLibrarian/SystemArchitect can review and propose corrections through
normal PRs.

Detection rules
---------------
Each rule has an ``id``, a ``severity`` (``error`` | ``warning``), a ``selector``
(glob of files in scope), and a ``check`` (callable). New rules are added by
appending to ``RULES``.

Exit codes
----------
* ``0`` when no errors are detected (warnings allowed).
* ``1`` when at least one error-severity finding exists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CANONICAL_POSITIONING = REPO_ROOT / ".github" / "instructions" / "repository-purpose.instructions.md"

# Files where the canonical positioning MUST be referenced or restated.
POSITIONING_BEARING_FILES = (
    "README.MD",
    "lib/README.md",
    "apps/README.md",
    "docs/README.md",
    "docs/agentic-microservices-reference.md",
    ".github/copilot-instructions.md",
)

# Phrases that contradict the canonical positioning when used in isolation.
# These are not banned globally — they are flagged when they appear without the
# corrective framing nearby.
CONTRADICTORY_PHRASES = (
    ("demonstration services", "apps/ are not demos; they are a product"),
    ("demo apps", "apps/ are not demos; they are a product"),
    ("conceptual framework", "lib/ is a real framework, not conceptual"),
    ("just a sample", "Azure-Samples is a distribution channel, not a quality tier"),
    ("just a framework", "we ship a framework AND a product"),
)

# Phrases that, when present, must appear close to a counter-balancing phrase.
PAIR_REQUIREMENTS = (
    {
        "phrase": "framework for agentic retail",
        "must_pair_with": ("product", "apps/", "retail platform"),
        "rationale": "framework framing must always be paired with the product half",
    },
)


@dataclass
class Finding:
    rule_id: str
    severity: str
    file: str
    line: int
    message: str
    excerpt: str = ""


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    def to_json(self) -> str:
        return json.dumps([asdict(f) for f in self.findings], indent=2)

    def to_markdown(self) -> str:
        if not self.findings:
            return (
                "# Documentation Consistency Audit\n\n"
                "No drift detected. All canonical positioning is preserved.\n"
            )

        lines = ["# Documentation Consistency Audit", ""]
        lines.append(
            f"**Findings:** {len(self.errors)} error(s), {len(self.warnings)} warning(s)."
        )
        lines.append("")
        lines.append(
            "Canonical positioning lives in "
            "[.github/instructions/repository-purpose.instructions.md]"
            "(.github/instructions/repository-purpose.instructions.md). "
            "Every entry below indicates a doc that has drifted from it."
        )
        lines.append("")
        lines.append("| Rule | Severity | File | Line | Message |")
        lines.append("|---|---|---|---|---|")
        for f in self.findings:
            file_link = f"[{f.file}]({f.file}#L{f.line})" if f.line else f.file
            lines.append(
                f"| `{f.rule_id}` | {f.severity} | {file_link} | {f.line or '-'} | {f.message} |"
            )

        if any(f.excerpt for f in self.findings):
            lines.append("")
            lines.append("## Excerpts")
            for f in self.findings:
                if f.excerpt:
                    lines.append("")
                    lines.append(f"### `{f.rule_id}` — {f.file}:L{f.line}")
                    lines.append("```")
                    lines.append(f.excerpt)
                    lines.append("```")

        lines.append("")
        lines.append("## Suggested next steps")
        lines.append("")
        lines.append(
            "1. ContentLibrarian opens a follow-up PR correcting the drift, citing the canonical file."
        )
        lines.append(
            "2. SystemArchitect verifies that no ADR is implied by the correction (if so, an ADR amendment ships first)."
        )
        lines.append(
            "3. The PR closes the auto-filed issue. Do not auto-delete docs from the audit; corrections are author-reviewed."
        )
        return "\n".join(lines)


def _iter_markdown_files(scope: Iterable[str] | None = None) -> Iterable[Path]:
    """Yield Markdown files in scope (defaults to authored docs, skipping generated)."""
    if scope is not None:
        for rel in scope:
            p = REPO_ROOT / rel
            if p.exists():
                yield p
        return

    skip_prefixes = (
        REPO_ROOT / "node_modules",
        REPO_ROOT / ".venv",
        REPO_ROOT / "lib" / "htmlcov",
        REPO_ROOT / "apps" / "ui" / ".next",
        REPO_ROOT / "apps" / "ui" / "node_modules",
        REPO_ROOT / "mkdocs" / "site",
    )
    for path in REPO_ROOT.rglob("*.md"):
        if any(str(path).startswith(str(prefix)) for prefix in skip_prefixes):
            continue
        yield path
    # uppercase .MD on Windows
    for path in REPO_ROOT.rglob("*.MD"):
        if any(str(path).startswith(str(prefix)) for prefix in skip_prefixes):
            continue
        yield path


def _relpath(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def rule_canonical_file_exists() -> list[Finding]:
    if CANONICAL_POSITIONING.exists():
        return []
    return [
        Finding(
            rule_id="canonical-positioning-missing",
            severity="error",
            file=_relpath(CANONICAL_POSITIONING),
            line=0,
            message=(
                "Canonical positioning file is missing. Every doc audit depends on this file."
            ),
        )
    ]


def rule_positioning_bearing_files_link_canonical() -> list[Finding]:
    findings: list[Finding] = []
    canonical_rel = _relpath(CANONICAL_POSITIONING)
    canonical_basename = CANONICAL_POSITIONING.name
    for rel in POSITIONING_BEARING_FILES:
        target = REPO_ROOT / rel
        if not target.exists():
            continue
        text = target.read_text(encoding="utf-8", errors="replace")
        if canonical_basename not in text and canonical_rel not in text:
            findings.append(
                Finding(
                    rule_id="positioning-bearing-missing-canonical-link",
                    severity="error",
                    file=rel,
                    line=1,
                    message=(
                        "Positioning-bearing file does not reference "
                        f"`{canonical_rel}`. Add a cross-reference at the top."
                    ),
                )
            )
    return findings


def rule_no_contradictory_phrases() -> list[Finding]:
    findings: list[Finding] = []
    for path in _iter_markdown_files():
        if path == CANONICAL_POSITIONING:
            # The canonical file declares which phrases we explicitly disclaim.
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        for phrase, rationale in CONTRADICTORY_PHRASES:
            if phrase in lower:
                # Find first occurrence and report.
                for line_no, line in enumerate(text.splitlines(), start=1):
                    if phrase in line.lower():
                        findings.append(
                            Finding(
                                rule_id="contradictory-phrase",
                                severity="warning",
                                file=_relpath(path),
                                line=line_no,
                                message=f"Contains '{phrase}'. {rationale}.",
                                excerpt=line.strip(),
                            )
                        )
                        break
    return findings


def rule_pair_requirements() -> list[Finding]:
    findings: list[Finding] = []
    for path in _iter_markdown_files():
        if path == CANONICAL_POSITIONING:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        for spec in PAIR_REQUIREMENTS:
            if spec["phrase"] not in lower:
                continue
            if not any(token.lower() in lower for token in spec["must_pair_with"]):
                # Find first occurrence
                for line_no, line in enumerate(text.splitlines(), start=1):
                    if spec["phrase"] in line.lower():
                        findings.append(
                            Finding(
                                rule_id="pair-requirement",
                                severity="error",
                                file=_relpath(path),
                                line=line_no,
                                message=(
                                    f"'{spec['phrase']}' must appear with at least one of "
                                    f"{spec['must_pair_with']}. {spec['rationale']}."
                                ),
                                excerpt=line.strip(),
                            )
                        )
                        break
    return findings


def rule_apps_described_as_product() -> list[Finding]:
    findings: list[Finding] = []
    apps_readme = REPO_ROOT / "apps" / "README.md"
    if not apps_readme.exists():
        return findings
    text = apps_readme.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"\bproduct\b", text, re.IGNORECASE):
        findings.append(
            Finding(
                rule_id="apps-readme-must-name-product",
                severity="error",
                file="apps/README.md",
                line=1,
                message="apps/README.md must explicitly describe apps/ as the product.",
            )
        )
    return findings


def rule_lib_described_as_framework() -> list[Finding]:
    findings: list[Finding] = []
    lib_readme = REPO_ROOT / "lib" / "README.md"
    if not lib_readme.exists():
        return findings
    text = lib_readme.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"\bframework\b", text, re.IGNORECASE):
        findings.append(
            Finding(
                rule_id="lib-readme-must-name-framework",
                severity="error",
                file="lib/README.md",
                line=1,
                message="lib/README.md must explicitly describe lib/ as the framework.",
            )
        )
    return findings


RULES: tuple[Callable[[], list[Finding]], ...] = (
    rule_canonical_file_exists,
    rule_positioning_bearing_files_link_canonical,
    rule_no_contradictory_phrases,
    rule_pair_requirements,
    rule_apps_described_as_product,
    rule_lib_described_as_framework,
)


def run_audit() -> Report:
    report = Report()
    for rule in RULES:
        report.findings.extend(rule())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write report to this file instead of stdout.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit non-zero on warnings, not only errors.",
    )
    args = parser.parse_args()

    report = run_audit()
    rendered = report.to_json() if args.format == "json" else report.to_markdown()

    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")

    if report.errors or (args.fail_on_warning and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
