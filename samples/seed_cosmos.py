#!/usr/bin/env python3
"""Seed script to load sample data into Cosmos DB truth store.

Loads product data, category schemas, and tenant configuration from the
``samples/data/`` directory into the configured Cosmos DB containers.

The script is idempotent — running it multiple times produces the same result.
Existing documents are upserted (not duplicated).

Usage::

    # Local Cosmos emulator (default)
    python samples/seed_cosmos.py

    # Cloud Cosmos DB (reads from environment variables)
    python samples/seed_cosmos.py --env cloud

    # Dry-run: print what would be loaded without writing
    python samples/seed_cosmos.py --dry-run

    # Load a specific category only
    python samples/seed_cosmos.py --category apparel

    # Seed schemas only
    python samples/seed_cosmos.py --schemas-only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("seed_cosmos")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SAMPLES_DIR = Path(__file__).resolve().parent
DATA_DIR = SAMPLES_DIR / "data"
SCHEMAS_DIR = DATA_DIR / "schemas"
MAPPINGS_DIR = DATA_DIR / "mappings"

PRODUCT_FILES = {
    "apparel": DATA_DIR / "products_apparel.json",
    "electronics": DATA_DIR / "products_electronics.json",
    "general": DATA_DIR / "products_general.json",
}

SCHEMA_FILES = {
    "apparel": SCHEMAS_DIR / "apparel.json",
    "electronics": SCHEMAS_DIR / "electronics.json",
    "general": SCHEMAS_DIR / "general.json",
}

TENANT_CONFIG_FILE = DATA_DIR / "tenant_config_default.json"
ACP_MAPPING_FILE = MAPPINGS_DIR / "acp_v1.json"

# ---------------------------------------------------------------------------
# Cosmos DB defaults
# ---------------------------------------------------------------------------

EMULATOR_URI = "https://localhost:8081"
EMULATOR_KEY = (
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGG"
    "yPMbIZnqyMsEcaGQy67XIw/Jw=="
)
EMULATOR_DATABASE = "truth-store"
EMULATOR_PRODUCTS_CONTAINER = "products"
EMULATOR_SCHEMAS_CONTAINER = "schemas"


def _cosmos_env(env: str) -> dict[str, str]:
    """Return Cosmos DB connection parameters for the given environment."""
    if env == "local":
        return {
            "uri": EMULATOR_URI,
            "key": EMULATOR_KEY,
            "database": EMULATOR_DATABASE,
            "products_container": EMULATOR_PRODUCTS_CONTAINER,
            "schemas_container": EMULATOR_SCHEMAS_CONTAINER,
        }
    # cloud — read from environment variables
    return {
        "uri": os.environ["COSMOS_ACCOUNT_URI"],
        "key": os.environ.get("COSMOS_ACCOUNT_KEY", ""),
        "database": os.environ.get("COSMOS_DATABASE", "truth-store"),
        "products_container": os.environ.get("COSMOS_PRODUCTS_CONTAINER", "products"),
        "schemas_container": os.environ.get("COSMOS_SCHEMAS_CONTAINER", "schemas"),
    }


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    """Load and return parsed JSON from *path*."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _build_product_docs(product_file: Path) -> list[dict[str, Any]]:
    """Return a flat list of Cosmos DB documents from a product JSON file.

    Each *style* becomes one document whose ``id`` equals ``style_id``.
    The ``_completeness_note`` metadata field is stripped before writing.
    """
    data = _load_json(product_file)
    docs: list[dict[str, Any]] = []
    for product in data.get("products", []):
        doc = {k: v for k, v in product.items() if not k.startswith("_")}
        doc["id"] = doc["style_id"]
        doc["type"] = "product_style"
        doc["source_category"] = data.get("category", "")
        doc["schema_id"] = data.get("schema_id", "")
        # Strip internal notes from variants too
        doc["variants"] = [
            {k: v for k, v in variant.items() if not k.startswith("_")}
            for variant in doc.get("variants", [])
        ]
        docs.append(doc)
    return docs


def _build_schema_docs() -> list[dict[str, Any]]:
    """Return Cosmos DB documents for all category schemas."""
    docs: list[dict[str, Any]] = []
    for category, path in SCHEMA_FILES.items():
        schema = _load_json(path)
        schema["id"] = schema.get("schema_id", category)
        schema["type"] = "category_schema"
        docs.append(schema)
    return docs


def _build_tenant_doc() -> dict[str, Any]:
    """Return a Cosmos DB document for the default tenant config."""
    config = _load_json(TENANT_CONFIG_FILE)
    config["id"] = config.get("tenant_id", "tenant-default")
    config["type"] = "tenant_config"
    return config


def _build_mapping_doc() -> dict[str, Any]:
    """Return a Cosmos DB document for the ACP v1 mapping."""
    mapping = _load_json(ACP_MAPPING_FILE)
    mapping["id"] = f"{mapping['protocol']}_{mapping['version'].replace('.', '_')}"
    mapping["type"] = "protocol_mapping"
    return mapping


# ---------------------------------------------------------------------------
# Cosmos DB writer
# ---------------------------------------------------------------------------


def _upsert_docs(
    container_client: Any,
    docs: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    label: str = "documents",
) -> int:
    """Upsert *docs* into *container_client*. Returns the count written."""
    count = 0
    for doc in docs:
        doc_id = doc.get("id", "<unknown>")
        if dry_run:
            logger.info("[DRY-RUN] would upsert %s id=%s", label, doc_id)
        else:
            container_client.upsert_item(doc)
            logger.info("Upserted %s id=%s", label, doc_id)
        count += 1
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed Cosmos DB with sample truth-layer data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--env",
        choices=["local", "cloud"],
        default="local",
        help="Target environment (default: local emulator)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be seeded without writing to Cosmos DB",
    )
    parser.add_argument(
        "--category",
        choices=list(PRODUCT_FILES.keys()),
        default=None,
        help="Seed only the specified product category (default: all)",
    )
    parser.add_argument(
        "--schemas-only",
        action="store_true",
        help="Seed only category schemas, not product data",
    )
    return parser


def main(argv: list[str] | None = None) -> int:  # noqa: C901
    """Entry point for the seed script.

    Returns 0 on success, non-zero on failure.
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # Resolve Cosmos connection parameters
    try:
        cosmos_cfg = _cosmos_env(args.env)
    except KeyError as exc:
        logger.error(
            "Missing required environment variable for cloud env: %s", exc
        )
        return 1

    # Lazy import so the script can be imported without azure-cosmos installed
    if not args.dry_run:
        try:
            from azure.cosmos import CosmosClient  # type: ignore[import]
        except ImportError:
            logger.error(
                "azure-cosmos package is not installed. "
                "Install it with: pip install azure-cosmos"
            )
            return 1

        client_kwargs: dict[str, Any] = {"url": cosmos_cfg["uri"]}
        if cosmos_cfg.get("key"):
            client_kwargs["credential"] = cosmos_cfg["key"]

        cosmos_client = CosmosClient(**client_kwargs)
        db = cosmos_client.get_database_client(cosmos_cfg["database"])
        products_ctr = db.get_container_client(cosmos_cfg["products_container"])
        schemas_ctr = db.get_container_client(cosmos_cfg["schemas_container"])
    else:
        products_ctr = None
        schemas_ctr = None

    total_written = 0

    # ---- Schemas ----
    schema_docs = _build_schema_docs()
    total_written += _upsert_docs(
        schemas_ctr,
        schema_docs,
        dry_run=args.dry_run,
        label="schema",
    )

    # ---- Tenant config (stored alongside schemas) ----
    tenant_doc = _build_tenant_doc()
    total_written += _upsert_docs(
        schemas_ctr,
        [tenant_doc],
        dry_run=args.dry_run,
        label="tenant_config",
    )

    # ---- Protocol mapping (stored alongside schemas) ----
    mapping_doc = _build_mapping_doc()
    total_written += _upsert_docs(
        schemas_ctr,
        [mapping_doc],
        dry_run=args.dry_run,
        label="protocol_mapping",
    )

    # ---- Products (skip if --schemas-only) ----
    if not args.schemas_only:
        categories_to_seed = (
            [args.category] if args.category else list(PRODUCT_FILES.keys())
        )
        for category in categories_to_seed:
            product_file = PRODUCT_FILES[category]
            if not product_file.exists():
                logger.warning("Product file not found: %s", product_file)
                continue
            product_docs = _build_product_docs(product_file)
            total_written += _upsert_docs(
                products_ctr,
                product_docs,
                dry_run=args.dry_run,
                label=f"product({category})",
            )

    logger.info("Seed complete. Total documents processed: %d", total_written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
