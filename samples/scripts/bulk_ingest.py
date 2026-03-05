"""Run bulk ingestion against truth-ingestion service."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def load_products(data_file: Path, limit: int | None = None) -> list[dict]:
    payload = json.loads(data_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list payload in {data_file}")
    return payload[:limit] if limit else payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk ingest sample products")
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--data-file", default="samples/data/products_general.json")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    products = load_products(Path(args.data_file), args.limit)
    endpoint = f"{args.base_url.rstrip('/')}/ingest/bulk"

    response = httpx.post(
        endpoint,
        json={"products": products, "concurrency": args.concurrency},
        timeout=args.timeout,
    )
    response.raise_for_status()

    print(json.dumps(response.json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
