#!/usr/bin/env python3
"""Audit strict PR-only governance controls for the main branch."""

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
        "--rulesets-file",
        type=Path,
        help="Optional JSON snapshot file for rulesets endpoint.",
    )
    parser.add_argument(
        "--branch-rules-file",
        type=Path,
        help="Optional JSON snapshot file for rules/branches/main endpoint.",
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


def audit(
    active_rulesets: list[dict[str, Any]],
    branch_rules: list[dict[str, Any]],
    required_checks: list[str],
    allowed_bypass_actor_ids: list[int],
) -> AuditResult:
    failures: list[str] = []
    warnings: list[str] = []

    if not active_rulesets and not branch_rules:
        failures.append("No active branch ruleset/protection detected for main.")

    rule_types = _collect_rule_types(active_rulesets, branch_rules)

    if "pull_request" not in rule_types:
        failures.append("Missing pull_request governance rule (PR-only merge not enforced).")

    pull_request_rule = _find_rule(active_rulesets, "pull_request")
    pull_params = (pull_request_rule or {}).get("parameters", {})
    if pull_request_rule:
        approvals = int(pull_params.get("required_approving_review_count") or 0)
        if approvals < 1:
            failures.append("Pull request rule does not require at least one approval.")
        if not bool(pull_params.get("required_review_thread_resolution")):
            failures.append("Pull request rule does not require conversation resolution.")
    else:
        warnings.append(
            "Pull request rule parameters unavailable in ruleset payload; approvals/thread resolution not fully verifiable."
        )

    if "required_status_checks" not in rule_types:
        failures.append("Missing required_status_checks rule.")

    status_rule = _find_rule(active_rulesets, "required_status_checks")
    contexts, strict = _required_check_contexts(status_rule)
    if status_rule:
        if not strict:
            failures.append("Status checks are not in strict mode (up-to-date branch required).")
        for check in required_checks:
            if check not in contexts:
                failures.append(f"Required status check '{check}' is missing from ruleset.")
    else:
        warnings.append(
            "Required status check rule parameters unavailable in ruleset payload; check contexts not fully verifiable."
        )

    if "non_fast_forward" not in rule_types:
        failures.append("Missing non_fast_forward rule (force-push blocking).")

    if "deletion" not in rule_types:
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
        branch_rules_payload = _github_get(args.repo, "rules/branches/main")

    rulesets = rulesets_payload if isinstance(rulesets_payload, list) else []
    branch_rules = branch_rules_payload if isinstance(branch_rules_payload, list) else []

    active_rulesets = _collect_active_branch_rulesets(rulesets)
    result = audit(
        active_rulesets=active_rulesets,
        branch_rules=branch_rules,
        required_checks=args.required_check,
        allowed_bypass_actor_ids=args.allow_bypass_actor_id,
    )

    run_mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"Governance audit mode: {run_mode}")
    print(f"Repository: {args.repo}")
    print(f"Active main branch rulesets: {len(active_rulesets)}")
    print(f"Branch rules entries (main): {len(branch_rules)}")

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
