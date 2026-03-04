"""Demonstrate review workflow for truth-layer data.

Attempts dedicated HITL endpoint first. If unavailable, falls back to CRUD
review endpoints.
"""

from __future__ import annotations

import argparse
import json

import httpx


def try_hitl_review(base_url: str, sku: str, timeout: float) -> tuple[bool, dict]:
    endpoint = f"{base_url.rstrip('/')}/invoke"
    payload = {
        "action": "approve",
        "proposal_id": f"proposal-{sku}",
        "reviewer": "staff-user",
        "notes": "approved via sample workflow",
    }
    try:
        response = httpx.post(endpoint, json=payload, timeout=timeout)
        if response.status_code == 200:
            return True, response.json()
        return False, {"status": response.status_code, "body": response.text}
    except httpx.HTTPError as exc:
        return False, {"error": str(exc)}


def fallback_crud_review(base_url: str, product_id: str, timeout: float) -> dict:
    list_endpoint = f"{base_url.rstrip('/')}/api/reviews"
    list_resp = httpx.get(list_endpoint, params={"product_id": product_id}, timeout=timeout)
    list_resp.raise_for_status()
    return {"workflow": "crud_fallback", "reviews": list_resp.json()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sample review workflow")
    parser.add_argument("--hitl-base-url", default="http://localhost:8014")
    parser.add_argument("--crud-base-url", default="http://localhost:8000")
    parser.add_argument("--sku", default="prd-001")
    parser.add_argument("--product-id", default="prd-001")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    ok, hitl_result = try_hitl_review(args.hitl_base_url, args.sku, args.timeout)
    if ok:
        print(json.dumps({"workflow": "hitl", "result": hitl_result}, indent=2))
        return 0

    fallback = fallback_crud_review(args.crud_base_url, args.product_id, args.timeout)
    print(
        json.dumps(
            {
                "workflow": "crud_fallback",
                "hitl_result": hitl_result,
                "fallback_result": fallback,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
