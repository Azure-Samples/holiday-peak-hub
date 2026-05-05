#!/usr/bin/env python3
"""Audit PR-only governance controls for a target branch."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request


@dataclass
class AuditResult:
    passed: bool
    failures: list[str]
    warnings: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit repository rulesets/branch rules for strict PR-only controls."
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY", ""),
        help="Repository in owner/name format. Defaults to GITHUB_REPOSITORY.",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Target branch to audit. Defaults to main.",
    )
    parser.add_argument(
        "--required-check",
        action="append",
        default=["lint", "test"],
        help="Required status check context name. Can be repeated.",
    )
    parser.add_argument(
        "--allow-bypass-actor-id",
        action="append",
        default=[],
        type=int,
        help="Bypass actor IDs explicitly allowed.",
    )
    parser.add_argument(
        "--min-approvals",
        type=int,
        default=0,
        help="Minimum required PR approvals. Defaults to 0 for solo mode.",
    )
    parser.add_argument(
        "--require-conversation-resolution",
        action="store_true",
        help="Require conversation resolution in PR governance checks.",
    )
    parser.add_argument(
        "--rulesets-file",
        type=Path,
        help="Optional JSON snapshot file for rulesets endpoint.",
    )
    parser.add_argument(
        "--branch-rules-file",
        type=Path,
        help="Optional JSON snapshot file for rules/branches/<branch> endpoint.",
    )
    parser.add_argument(
        "--branch-protection-file",
        type=Path,
        help="Optional JSON snapshot file for branches/<branch>/protection endpoint.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Annotate output as dry-run evidence.",
    )
    return parser.parse_args()


def _github_get(repo: str, endpoint: str) -> Any:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN/GH_TOKEN for GitHub API access.")

    url = f"https://api.github.com/repos/{repo}/{endpoint.lstrip('/')}"
    req = request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} on {endpoint}: {body}") from exc


def _github_get_optional(repo: str, endpoint: str) -> Any | None:
    try:
        return _github_get(repo, endpoint)
    except RuntimeError as exc:
        # GitHub Actions integration tokens often cannot read branch protection.
        if "GitHub API 404" in str(exc) or "GitHub API 403" in str(exc):
            return None
        raise


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_ref_conditions(ruleset: dict[str, Any]) -> dict[str, list[str]]:
    conditions = ruleset.get("conditions", {}) or {}
    ref_name = conditions.get("ref_name", {}) or {}
    include = ref_name.get("include") or []
    exclude = ref_name.get("exclude") or []
    return {"include": include, "exclude": exclude}


def _applies_to_main(ruleset: dict[str, Any]) -> bool:
    conditions = _extract_ref_conditions(ruleset)
    include = conditions["include"]
    exclude = conditions["exclude"]

    def match_pattern(pattern: str) -> bool:
        return pattern in {
            "main",
            "refs/heads/main",
            "~DEFAULT_BRANCH",
            "~ALL",
        }

    included = True if not include else any(match_pattern(p) for p in include)
    excluded = any(match_pattern(p) for p in exclude)
    return included and not excluded


def _collect_active_branch_rulesets(rulesets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for ruleset in rulesets:
        if ruleset.get("target") != "branch":
            continue
        if ruleset.get("enforcement") != "active":
            continue
        if _applies_to_main(ruleset):
            selected.append(ruleset)
    return selected


def _collect_rule_types(rulesets: list[dict[str, Any]], branch_rules: list[dict[str, Any]]) -> set[str]:
    rule_types: set[str] = set()
    for ruleset in rulesets:
        for rule in ruleset.get("rules", []) or []:
            rule_type = rule.get("type")
            if rule_type:
                rule_types.add(rule_type)
    for rule in branch_rules:
        rule_type = rule.get("type")
        if rule_type:
            rule_types.add(rule_type)
    return rule_types


def _find_rule(rulesets: list[dict[str, Any]], rule_type: str) -> dict[str, Any] | None:
    for ruleset in rulesets:
        for rule in ruleset.get("rules", []) or []:
            if rule.get("type") == rule_type:
                return rule
    return None


def _required_check_contexts(status_rule: dict[str, Any] | None) -> tuple[set[str], bool]:
    if not status_rule:
        return set(), False
    parameters = status_rule.get("parameters", {}) or {}
    strict = bool(parameters.get("strict_required_status_checks_policy"))

    contexts: set[str] = set()
    for entry in parameters.get("required_status_checks", []) or []:
        if isinstance(entry, str):
            contexts.add(entry)
            continue
        context = entry.get("context")
        if context:
            contexts.add(context)
    return contexts, strict


def _branch_protection_status_contexts(branch_protection: dict[str, Any] | None) -> tuple[set[str], bool]:
    if not branch_protection:
        return set(), False

    required_status_checks = branch_protection.get("required_status_checks") or {}
    strict = bool(required_status_checks.get("strict"))

    contexts: set[str] = set()
    for context in required_status_checks.get("contexts") or []:
        if isinstance(context, str):
            contexts.add(context)

    for entry in required_status_checks.get("checks") or []:
        if isinstance(entry, str):
            contexts.add(entry)
            continue
        context = entry.get("context") if isinstance(entry, dict) else None
        if context:
            contexts.add(context)

    return contexts, strict


def audit(
    active_rulesets: list[dict[str, Any]],
    branch_rules: list[dict[str, Any]],
    branch_protection: dict[str, Any] | None,
    required_checks: list[str],
    allowed_bypass_actor_ids: list[int],
    min_approvals: int,
    require_conversation_resolution: bool,
) -> AuditResult:
    failures: list[str] = []
    warnings: list[str] = []

    if not active_rulesets and not branch_rules and not branch_protection:
        failures.append("No active branch ruleset/protection detected for main.")

    rule_types = _collect_rule_types(active_rulesets, branch_rules)

    has_pull_request_governance = "pull_request" in rule_types or branch_protection is not None
    if not has_pull_request_governance:
        failures.append("Missing pull_request governance rule (PR-only merge not enforced).")

    pull_request_rule = _find_rule(active_rulesets, "pull_request")
    pull_params = (pull_request_rule or {}).get("parameters", {})
    if pull_request_rule:
        approvals = int(pull_params.get("required_approving_review_count") or 0)
        if approvals < min_approvals:
            failures.append(
                f"Pull request rule requires {approvals} approval(s), expected at least {min_approvals}."
            )
        if require_conversation_resolution and not bool(
            pull_params.get("required_review_thread_resolution")
        ):
            failures.append("Pull request rule does not require conversation resolution.")
    elif branch_protection:
        pr_reviews = branch_protection.get("required_pull_request_reviews") or {}
        approvals = int(pr_reviews.get("required_approving_review_count") or 0)
        if approvals < min_approvals:
            failures.append(
                f"Branch protection requires {approvals} approval(s), expected at least {min_approvals}."
            )

        conversation_resolution_enabled = bool(
            (branch_protection.get("required_conversation_resolution") or {}).get("enabled")
        )
        if require_conversation_resolution and not conversation_resolution_enabled:
            failures.append("Branch protection does not require conversation resolution.")
    else:
        warnings.append(
            "Pull request rule parameters unavailable in ruleset payload; approvals/thread resolution not fully verifiable."
        )

    has_required_status_checks = "required_status_checks" in rule_types or branch_protection is not None
    if not has_required_status_checks:
        failures.append("Missing required_status_checks rule.")

    status_rule = _find_rule(active_rulesets, "required_status_checks")
    contexts, strict = _required_check_contexts(status_rule)
    if status_rule:
        if not strict:
            failures.append("Status checks are not in strict mode (up-to-date branch required).")
        for check in required_checks:
            if check not in contexts:
                failures.append(f"Required status check '{check}' is missing from ruleset.")
    elif branch_protection:
        contexts, strict = _branch_protection_status_contexts(branch_protection)
        if not strict:
            failures.append("Status checks are not in strict mode (up-to-date branch required).")
        for check in required_checks:
            if check not in contexts:
                failures.append(f"Required status check '{check}' is missing from branch protection.")
    else:
        warnings.append(
            "Required status check rule parameters unavailable in ruleset payload; check contexts not fully verifiable."
        )

    has_non_fast_forward = "non_fast_forward" in rule_types
    if branch_protection:
        force_push_enabled = bool((branch_protection.get("allow_force_pushes") or {}).get("enabled"))
        has_non_fast_forward = has_non_fast_forward or not force_push_enabled
    if not has_non_fast_forward:
        failures.append("Missing non_fast_forward rule (force-push blocking).")

    has_deletion_block = "deletion" in rule_types
    if branch_protection:
        deletion_enabled = bool((branch_protection.get("allow_deletions") or {}).get("enabled"))
        has_deletion_block = has_deletion_block or not deletion_enabled
    if not has_deletion_block:
        failures.append("Missing deletion rule (branch deletion blocking).")

    bypass_actors: list[dict[str, Any]] = []
    for ruleset in active_rulesets:
        bypass_actors.extend(ruleset.get("bypass_actors", []) or [])

    for actor in bypass_actors:
        actor_id = actor.get("actor_id")
        if isinstance(actor_id, int) and actor_id in allowed_bypass_actor_ids:
            continue
        failures.append(
            f"Unexpected bypass actor present (actor_id={actor_id}, actor_type={actor.get('actor_type')})."
        )

    return AuditResult(passed=not failures, failures=failures, warnings=warnings)


def main() -> int:
    args = parse_args()

    if not args.repo:
        print("Missing --repo and GITHUB_REPOSITORY is not set.")
        return 2

    if args.rulesets_file:
        rulesets_payload = _load_json(args.rulesets_file)
    else:
        rulesets_payload = _github_get(args.repo, "rulesets?per_page=100")

    if args.branch_rules_file:
        branch_rules_payload = _load_json(args.branch_rules_file)
    else:
        branch_rules_payload = _github_get_optional(args.repo, f"rules/branches/{parse.quote(args.branch, safe='')}")

    if args.branch_protection_file:
        branch_protection_payload = _load_json(args.branch_protection_file)
    else:
        branch_protection_payload = _github_get_optional(
            args.repo,
            f"branches/{parse.quote(args.branch, safe='')}/protection",
        )

    rulesets = rulesets_payload if isinstance(rulesets_payload, list) else []
    branch_rules = branch_rules_payload if isinstance(branch_rules_payload, list) else []
    branch_protection = (
        branch_protection_payload if isinstance(branch_protection_payload, dict) else None
    )

    active_rulesets = _collect_active_branch_rulesets(rulesets)
    result = audit(
        active_rulesets=active_rulesets,
        branch_rules=branch_rules,
        branch_protection=branch_protection,
        required_checks=args.required_check,
        allowed_bypass_actor_ids=args.allow_bypass_actor_id,
        min_approvals=args.min_approvals,
        require_conversation_resolution=args.require_conversation_resolution,
    )

    run_mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"Governance audit mode: {run_mode}")
    print(f"Repository: {args.repo}")
    print(f"Branch: {args.branch}")
    print(f"Active main branch rulesets: {len(active_rulesets)}")
    print(f"Branch rules entries (main): {len(branch_rules)}")
    print(f"Branch protection detected: {branch_protection is not None}")

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")

    if result.failures:
        print("Failures:")
        for failure in result.failures:
            print(f"- {failure}")
        return 1

    print("Governance audit passed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Governance audit execution error: {exc}")
        sys.exit(2)
