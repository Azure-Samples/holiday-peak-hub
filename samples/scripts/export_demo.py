"""Demonstrate ACP/UCP export workflow.

- ACP export: calls product-management-acp-transformation `/invoke`
- UCP export: demonstrates current local UCP shape from returned ACP source data
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import httpx


def export_acp(base_url: str, sku: str, timeout: float) -> dict:
    endpoint = f"{base_url.rstrip('/')}/invoke"
    response = httpx.post(
        endpoint,
        json={"sku": sku, "availability": "in_stock", "currency": "usd"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def build_ucp_view(sku: str, acp_payload: dict) -> dict:
    acp_product = acp_payload.get("acp_product") or acp_payload.get("result", {}).get("acp_product")
    if not isinstance(acp_product, dict):
        return {
            "entity_id": sku,
            "sku": sku,
            "title": None,
            "brand": None,
            "metadata": {"protocol": "ucp", "version": "1.0", "exported_at": datetime.now(timezone.utc).isoformat()},
        }

    return {
        "entity_id": sku,
        "sku": sku,
        "title": acp_product.get("title"),
        "brand": acp_product.get("brand"),
        "short_description": acp_product.get("description"),
        "images": [{"url": acp_product.get("image_url"), "role": "primary", "alt_text": None}] if acp_product.get("image_url") else [],
        "pricing": {
            "list_price": None,
            "sale_price": None,
            "currency": "USD",
        },
        "attributes": {},
        "metadata": {
            "protocol": "ucp",
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run export demo")
    parser.add_argument("--export-base-url", default="http://localhost:8013")
    parser.add_argument("--sku", default="prd-001")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    acp = export_acp(args.export_base_url, args.sku, args.timeout)
    ucp = build_ucp_view(args.sku, acp)

    print(json.dumps({"acp": acp, "ucp": ucp}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
