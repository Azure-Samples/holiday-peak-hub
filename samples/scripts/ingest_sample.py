"""Run single-product ingestion against truth-ingestion service."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def load_first_product(data_file: Path) -> dict:
    payload = json.loads(data_file.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        return payload[0]
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Unsupported payload shape in {data_file}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest one sample product")
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument(
        "--data-file",
        default="samples/data/products_general.json",
        help="Path to JSON file with sample products",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    product = load_first_product(Path(args.data_file))
    endpoint = f"{args.base_url.rstrip('/')}/ingest/product"

    response = httpx.post(endpoint, json={"product": product}, timeout=args.timeout)
    response.raise_for_status()

    print(json.dumps(response.json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
