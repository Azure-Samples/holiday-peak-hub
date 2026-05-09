"""Rewrite docs-to-source links to absolute GitHub blob URLs (#1021).

The `docs/` tree contains many legitimate cross-references to source files
that live outside `docs/` itself: `../apps/`, `../lib/src/`, `../scripts/`,
`../infra/`, `../.kubernetes/`, `../.github/`, etc. Mkdocs cannot resolve
those targets because they are not part of the documentation files; left
unhandled, they raise `--strict` warnings that prevent us from flipping
the build gate strict.

Two paths exist:

  1. Suppress validation — broken in the rendered HTML, useless for readers.
  2. Rewrite the link to an absolute GitHub blob URL — works in the rendered
     HTML and survives `--strict`.

This hook implements path 2. It is intentionally conservative:

  - Only rewrites *relative* links (no scheme).
  - Only rewrites links whose target path matches one of the known
    source-tree prefixes.
  - Resolves `../` segments against the current page's directory so the
    rewrite produces the correct absolute path inside the repo tree.
  - Never rewrites anchors (e.g. `#some-section`); only the link target.
  - Never rewrites image references — the rule only applies to anchor
    links emitted by `[label](target)` syntax.

Configuration is via the `MKDOCS_REPO_REF` environment variable so PR
preview deploys can rewrite to the PR's own ref instead of `main`. The
fallback is `main` to keep the local build deterministic.
"""

from __future__ import annotations

import os
import re
from pathlib import PurePosixPath
from typing import Iterable

# Source-tree prefixes — anything outside docs/ that we know lives in the
# canonical Azure-Samples/holiday-peak-hub repo. Add new top-level dirs here.
_SOURCE_TREE_PREFIXES: tuple[str, ...] = (
    "apps",
    "lib",
    "scripts",
    "infra",
    ".infra",
    ".kubernetes",
    ".github",
    "mkdocs",
    "samples",
    "tests",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.MD",
    "LICENSE",
    "README.MD",
    "azure.yaml",
    "pyproject.toml",
    "conftest.py",
    "improvements.md",
)

_REPO_BLOB_BASE = (
    "https://github.com/Azure-Samples/holiday-peak-hub/blob/"
    + os.environ.get("MKDOCS_REPO_REF", "main")
)

# Markdown link regex: capture [label](target) where target has no `://`.
# The label permits one level of nested square brackets (Next.js dynamic
# segments like `[id]` inside backtick spans) — but the "plain" branch
# excludes both `[` and `]` so the `\[…\]` alternative is deterministic
# and cannot trigger exponential backtracking (CodeQL py/redos).
# The target permits one level of balanced parens (Next.js route groups
# like `(deploy)`); the plain branch excludes both `(` and `)` for the
# same reason. Handles optional title suffix `[label](target "title")`.
_MD_LINK = re.compile(
    r"(?<!!)\[(?P<label>(?:\[[^\]]*\]|[^\[\]])*)\]\("
    r"(?P<target>(?:\([^()\s]*\)|[^()\s])+)"
    r"(?P<suffix>(?:\s+\"[^\"]*\")?)\)",
)


def _is_external(target: str) -> bool:
    return "://" in target or target.startswith(("mailto:", "tel:", "/"))


def _has_source_prefix(resolved: str) -> bool:
    head = resolved.split("/", 1)[0] if "/" in resolved else resolved
    return any(
        resolved == prefix or resolved.startswith(prefix + "/")
        for prefix in _SOURCE_TREE_PREFIXES
    ) or head in _SOURCE_TREE_PREFIXES


def _resolve_relative(page_src_uri: str, target: str) -> str:
    """Resolve `target` relative to the page's directory inside docs/.

    Returns a path relative to the *repo root*, not to docs/. So
    `target = "../apps/foo.md"` from page `docs/architecture/x.md`
    resolves to `apps/foo.md`.
    """
    page_dir = PurePosixPath(page_src_uri).parent  # e.g. architecture
    # Page dir is rooted at docs/; we resolve relative to repo root by
    # prepending docs/ first, then walking the relative path, then
    # stripping the docs/ prefix if the result is still inside docs/.
    full = (PurePosixPath("docs") / page_dir / target).as_posix()
    parts: list[str] = []
    for piece in full.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            if parts:
                parts.pop()
            continue
        parts.append(piece)
    return "/".join(parts)


def _resolve_inside_docs(page_src_uri: str, target: str) -> str:
    """Resolve `target` to a path *relative to docs/* (or empty if it escapes).

    Returns "" if the target resolves outside the docs/ tree (so callers
    can fall back to other strategies).
    """
    page_dir = PurePosixPath(page_src_uri).parent
    full = (page_dir / target).as_posix()
    parts: list[str] = []
    for piece in full.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            if not parts:
                return ""
            parts.pop()
            continue
        parts.append(piece)
    return "/".join(parts)


def _split_anchor(target: str) -> tuple[str, str]:
    if "#" in target:
        path, anchor = target.split("#", 1)
        return path, "#" + anchor
    return target, ""


def _rewrite_one(
    page_src_uri: str, match: re.Match[str], known_doc_paths: frozenset[str]
) -> str:
    # pylint: disable=too-many-return-statements
    target_full = match.group("target")
    if _is_external(target_full):
        return match.group(0)

    target_path, anchor = _split_anchor(target_full)
    if not target_path:
        # Pure anchor link — leave untouched.
        return match.group(0)

    # First, check if the *raw* target already starts with a source-tree
    # prefix. This catches author-side mistakes where someone wrote
    # `.infra/foo` instead of `../.infra/foo`. Such links never resolve to
    # anything inside docs/, so rewriting them to a GitHub blob URL is the
    # only useful repair short of a manual content fix.
    head = target_path.split("/", 1)[0] if "/" in target_path else target_path
    if head in _SOURCE_TREE_PREFIXES or any(
        target_path.startswith(prefix + "/") for prefix in _SOURCE_TREE_PREFIXES
    ):
        rewritten = f"{_REPO_BLOB_BASE}/{target_path}{anchor}"
        label = match.group("label")
        suffix = match.group("suffix") or ""
        return f"[{label}]({rewritten}{suffix})"

    resolved = _resolve_relative(page_src_uri, target_path)
    if _has_source_prefix(resolved):
        rewritten = f"{_REPO_BLOB_BASE}/{resolved}{anchor}"
        label = match.group("label")
        suffix = match.group("suffix") or ""
        return f"[{label}]({rewritten}{suffix})"

    # Directory-only relative paths (`dir/`) — patch to `dir/README.md`
    # so both mkdocs and GitHub follow the intended target.
    rewrote_dir = False
    if target_path.endswith("/") and not target_path.startswith(("/", "..")):
        target_path = target_path.rstrip("/") + "/README.md"
        rewrote_dir = True

    # Final repair: the link resolves *inside* docs/ but the target file
    # does not exist (planned content like demo notebooks scheduled for
    # later phases). Rewriting to the GitHub blob URL turns a broken
    # mkdocs internal link into a deterministic external pointer that
    # starts working the moment the planned file is committed.
    inside_docs = _resolve_inside_docs(page_src_uri, target_path)
    if inside_docs and inside_docs not in known_doc_paths:
        rewritten = f"{_REPO_BLOB_BASE}/docs/{inside_docs}{anchor}"
        label = match.group("label")
        suffix = match.group("suffix") or ""
        return f"[{label}]({rewritten}{suffix})"

    # The directory-only patch produced a valid intra-docs link — emit it.
    if rewrote_dir:
        label = match.group("label")
        suffix = match.group("suffix") or ""
        return f"[{label}]({target_path}{anchor}{suffix})"

    return match.group(0)


def _collect_known_doc_paths(files) -> frozenset[str]:
    """Build a set of doc paths (relative to docs/) so the hook can detect
    links pointing at planned-but-missing files."""
    paths: set[str] = set()
    if files is None:
        return frozenset()
    for f in files:
        # mkdocs `File` objects expose `src_uri` (relative to docs_dir).
        src_uri = getattr(f, "src_uri", None) or getattr(f, "src_path", None)
        if src_uri:
            paths.add(src_uri.replace(os.sep, "/"))
    return frozenset(paths)


def on_page_markdown(markdown: str, page, config, files) -> str:  # noqa: ARG001
    """mkdocs hook entry point — rewrites source-tree links."""
    # pylint: disable=unused-argument
    page_src_uri = getattr(page.file, "src_uri", page.file.src_path).replace(
        os.sep, "/"
    )
    known = _collect_known_doc_paths(files)
    return _MD_LINK.sub(
        lambda m: _rewrite_one(page_src_uri, m, known), markdown
    )


def get_iterable_prefixes() -> Iterable[str]:
    """Exposed for unit-test introspection."""
    return _SOURCE_TREE_PREFIXES
