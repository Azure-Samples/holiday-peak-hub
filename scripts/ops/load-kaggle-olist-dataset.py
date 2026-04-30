"""Load the Kaggle Olist Brazilian E-Commerce dataset into the CRUD service.

Downloads, transforms, and POSTs data to the Holiday Peak Hub CRUD service to seed
a realistic demo environment with products, orders, and users.

Dataset: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
License: CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/)

Requirements:
    pip install httpx pandas opendatasets tqdm

Usage:
    python scripts/ops/load-kaggle-olist-dataset.py --crud-url http://localhost:8000
    python scripts/ops/load-kaggle-olist-dataset.py --limit 200 --kaggle-dir ./data/olist
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import random
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category mapping: Olist Portuguese → our retail taxonomy
# ---------------------------------------------------------------------------
CATEGORY_MAP: dict[str, str] = {
    "informatica_acessorios": "Electronics",
    "telefonia": "Electronics",
    "eletronicos": "Electronics",
    "tablets_impressao_imagem": "Electronics",
    "pcs": "Electronics",
    "consoles_games": "Electronics",
    "audio": "Electronics",
    "telefonia_fixa": "Electronics",
    "pc_gamer": "Electronics",
    "sinalizacao_e_seguranca": "Electronics",
    "cama_mesa_banho": "Home & Kitchen",
    "moveis_decoracao": "Furniture",
    "moveis_escritorio": "Furniture",
    "moveis_sala": "Furniture",
    "moveis_quarto": "Furniture",
    "moveis_cozinha_area_de_servico_jantar_e_jardim": "Furniture",
    "utilidades_domesticas": "Home & Kitchen",
    "eletrodomesticos": "Home & Kitchen",
    "eletrodomesticos_2": "Home & Kitchen",
    "casa_conforto": "Home & Kitchen",
    "casa_conforto_2": "Home & Kitchen",
    "casa_construcao": "Home & Kitchen",
    "cozinha_sala_copa_pia_e_banho": "Home & Kitchen",
    "climatizacao": "Home & Kitchen",
    "construcao_ferramentas_construcao": "Home & Kitchen",
    "construcao_ferramentas_iluminacao": "Home & Kitchen",
    "construcao_ferramentas_seguranca": "Home & Kitchen",
    "construcao_ferramentas_jardim": "Home & Kitchen",
    "construcao_ferramentas_ferramentas": "Home & Kitchen",
    "cool_stuff": "Toys & Games",
    "brinquedos": "Toys & Games",
    "bebes": "Toys & Games",
    "fashion_bolsas_e_acessorios": "Clothes & Apparel",
    "fashion_calcados": "Clothes & Apparel",
    "fashion_roupa_masculina": "Clothes & Apparel",
    "fashion_roupa_feminina": "Clothes & Apparel",
    "fashion_underwear_e_moda_praia": "Clothes & Apparel",
    "fashion_esporte": "Clothes & Apparel",
    "fashion_roupa_infanto_juvenil": "Clothes & Apparel",
    "esporte_lazer": "Clothes & Apparel",
    "beleza_saude": "Home & Kitchen",
    "perfumaria": "Home & Kitchen",
    "fraldas_higiene": "Home & Kitchen",
    "alimentos": "Home & Kitchen",
    "alimentos_bebidas": "Home & Kitchen",
    "bebidas": "Home & Kitchen",
    "artigos_de_festas": "Toys & Games",
    "artigos_de_natal": "Toys & Games",
    "livros_interesse_geral": "Toys & Games",
    "livros_tecnicos": "Electronics",
    "livros_importados": "Toys & Games",
    "musica": "Electronics",
    "dvds_blu_ray": "Electronics",
    "cds_dvds_musicais": "Electronics",
    "papelaria": "Toys & Games",
    "flores": "Home & Kitchen",
    "pet_shop": "Home & Kitchen",
    "relogios_presentes": "Clothes & Apparel",
    "malas_acessorios": "Clothes & Apparel",
    "automotivo": "Electronics",
    "agro_industria_e_comercio": "Home & Kitchen",
    "industria_comercio_e_negocios": "Home & Kitchen",
    "seguros_e_servicos": "Home & Kitchen",
    "portateis_cozinha_e_preparadores_de_alimentos": "Home & Kitchen",
    "market_place": "Home & Kitchen",
    "la_cuisine": "Home & Kitchen",
    "artes": "Toys & Games",
    "artes_e_artesanato": "Toys & Games",
}

# Synthetic name templates per category for product name generation
NAME_TEMPLATES: dict[str, list[str]] = {
    "Electronics": [
        "{adj} Wireless Device",
        "Smart {adj} Gadget",
        "{adj} Tech Accessory",
        "Digital {adj} Hub",
        "Pro {adj} Controller",
    ],
    "Home & Kitchen": [
        "{adj} Kitchen Essential",
        "Home {adj} Organizer",
        "{adj} Comfort Set",
        "Premium {adj} Appliance",
        "{adj} Living Aid",
    ],
    "Furniture": [
        "{adj} Modern Furniture",
        "Classic {adj} Table",
        "{adj} Storage Solution",
        "Designer {adj} Shelf",
        "{adj} Comfort Chair",
    ],
    "Clothes & Apparel": [
        "{adj} Fashion Item",
        "Premium {adj} Wear",
        "{adj} Style Collection",
        "Classic {adj} Accessory",
        "{adj} Active Gear",
    ],
    "Toys & Games": [
        "{adj} Fun Set",
        "Creative {adj} Kit",
        "{adj} Play Collection",
        "Adventure {adj} Pack",
        "{adj} Learning Toy",
    ],
}

ADJECTIVES = [
    "Premium", "Ultra", "Compact", "Deluxe", "Essential", "Professional",
    "Advanced", "Classic", "Modern", "Eco-Friendly", "Lightweight",
    "Durable", "Versatile", "Portable", "Smart", "Ergonomic",
]


def _deterministic_id(seed: str) -> str:
    """Generate a deterministic UUID from a seed string."""
    return str(uuid.UUID(hashlib.md5(seed.encode()).hexdigest()))


def _generate_product_name(category: str, seed: int) -> str:
    """Generate a synthetic product name based on category."""
    random.seed(seed)
    templates = NAME_TEMPLATES.get(category, NAME_TEMPLATES["Electronics"])
    template = random.choice(templates)
    adj = random.choice(ADJECTIVES)
    return template.format(adj=adj)


def _generate_description(name: str, category: str, weight_g: float | None) -> str:
    """Generate a synthetic product description."""
    base = f"High-quality {name.lower()} in the {category} category."
    if weight_g and weight_g > 0:
        base += f" Weighs approximately {weight_g:.0f}g."
    base += " Perfect for everyday use with modern design and reliable performance."
    return base


# ---------------------------------------------------------------------------
# Data download
# ---------------------------------------------------------------------------
def download_olist_dataset(kaggle_dir: Path) -> Path:
    """Download the Olist dataset from Kaggle using opendatasets."""
    try:
        import opendatasets as od
    except ImportError:
        logger.error(
            "Package 'opendatasets' is required. Install with: pip install opendatasets"
        )
        sys.exit(1)

    dataset_url = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
    od.download(dataset_url, data_dir=str(kaggle_dir))

    dataset_path = kaggle_dir / "brazilian-ecommerce"
    if not dataset_path.exists():
        # Some versions extract differently
        candidates = list(kaggle_dir.glob("*olist*"))
        if candidates:
            dataset_path = candidates[0]
        else:
            logger.error("Dataset not found after download in %s", kaggle_dir)
            sys.exit(1)

    return dataset_path


def find_dataset(kaggle_dir: Path) -> Path:
    """Find the Olist dataset directory."""
    # Check common locations
    candidates = [
        kaggle_dir / "brazilian-ecommerce",
        kaggle_dir,
    ]
    for candidate in candidates:
        if (candidate / "olist_products_dataset.csv").exists():
            return candidate

    logger.error(
        "Olist dataset not found in %s. "
        "Download from https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce "
        "or use --download flag.",
        kaggle_dir,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------
def transform_products(
    dataset_path: Path, limit: int
) -> list[dict[str, Any]]:
    """Transform Olist products into CRUD service schema."""
    products_df = pd.read_csv(dataset_path / "olist_products_dataset.csv")

    # Load category translations
    translation_path = dataset_path / "product_category_name_translation.csv"
    if translation_path.exists():
        translations = pd.read_csv(translation_path)
        trans_map = dict(
            zip(
                translations["product_category_name"],
                translations["product_category_name_english"],
                strict=False,
            )
        )
    else:
        trans_map = {}

    # Load review scores for ratings
    reviews_path = dataset_path / "olist_order_reviews_dataset.csv"
    items_path = dataset_path / "olist_order_items_dataset.csv"

    product_ratings: dict[str, float] = {}
    product_prices: dict[str, float] = {}

    if items_path.exists():
        items_df = pd.read_csv(items_path)
        price_agg = items_df.groupby("product_id")["price"].mean()
        product_prices = price_agg.to_dict()

    if reviews_path.exists() and items_path.exists():
        reviews_df = pd.read_csv(reviews_path)
        # Join reviews with items to get product-level ratings
        review_items = reviews_df.merge(
            items_df[["order_id", "product_id"]], on="order_id", how="inner"
        )
        rating_agg = review_items.groupby("product_id")["review_score"].mean()
        product_ratings = rating_agg.to_dict()

    products: list[dict[str, Any]] = []
    for idx, row in products_df.head(limit).iterrows():
        product_id = row["product_id"]
        raw_category = row.get("product_category_name", "")

        if pd.isna(raw_category):
            raw_category = "general"

        # Map to our category
        category = CATEGORY_MAP.get(raw_category, "Home & Kitchen")

        # Generate synthetic name and description
        name = _generate_product_name(category, seed=idx)
        weight_g = row.get("product_weight_g")
        if pd.isna(weight_g):
            weight_g = None
        description = _generate_description(name, category, weight_g)

        # Price from order items or generate
        price = product_prices.get(product_id)
        if price is None or pd.isna(price):
            random.seed(idx)
            price = round(random.uniform(9.99, 299.99), 2)

        # Rating from reviews
        rating = product_ratings.get(product_id)
        if rating is None or pd.isna(rating):
            rating = None
        else:
            rating = round(float(rating), 1)

        # Build features from dimensions
        features = []
        width = row.get("product_width_cm")
        height = row.get("product_height_cm")
        length = row.get("product_length_cm")
        if not pd.isna(width) and not pd.isna(height) and not pd.isna(length):
            features.append(f"{length:.0f}×{width:.0f}×{height:.0f} cm")
        if weight_g:
            features.append(f"{weight_g:.0f}g")
        photos_qty = row.get("product_photos_qty")
        if not pd.isna(photos_qty) and photos_qty > 0:
            features.append(f"{int(photos_qty)} product photos")

        english_cat = trans_map.get(raw_category, raw_category)

        products.append({
            "id": _deterministic_id(product_id),
            "name": name,
            "description": description,
            "price": round(float(price), 2),
            "category": category,
            "brand": "",
            "features": features,
            "image_url": f"https://picsum.photos/seed/{product_id[:8]}/800/800",
            "tags": [category.lower().replace(" & ", "-"), english_cat]
            if english_cat
            else [category.lower().replace(" & ", "-")],
            "rating": rating,
        })

    return products


def transform_users(dataset_path: Path, limit: int) -> list[dict[str, Any]]:
    """Transform Olist customers into CRUD service user schema."""
    customers_df = pd.read_csv(dataset_path / "olist_customers_dataset.csv")

    # Deduplicate by customer_unique_id
    unique_customers = customers_df.drop_duplicates(subset=["customer_unique_id"])

    users: list[dict[str, Any]] = []
    for idx, row in unique_customers.head(limit).iterrows():
        customer_id = row["customer_unique_id"]
        city = row.get("customer_city", "Unknown")
        state = row.get("customer_state", "XX")
        zip_prefix = row.get("customer_zip_code_prefix", "00000")

        user_id = _deterministic_id(customer_id)
        # Generate a synthetic email
        email = f"user-{user_id[:8]}@example.com"
        name = f"Customer {user_id[:6].upper()}"

        users.append({
            "id": user_id,
            "email": email,
            "name": name,
            "role": "customer",
            "addresses": [
                {
                    "city": str(city).title(),
                    "state": str(state).upper(),
                    "zip": str(zip_prefix),
                    "country": "BR",
                }
            ],
        })

    return users


def transform_orders(
    dataset_path: Path, limit: int, product_id_map: dict[str, str]
) -> list[dict[str, Any]]:
    """Transform Olist orders into CRUD service order schema."""
    orders_df = pd.read_csv(dataset_path / "olist_orders_dataset.csv")
    items_df = pd.read_csv(dataset_path / "olist_order_items_dataset.csv")

    # Status mapping
    status_map = {
        "delivered": "delivered",
        "shipped": "shipped",
        "processing": "processing",
        "created": "pending",
        "approved": "processing",
        "invoiced": "processing",
        "canceled": "cancelled",
        "unavailable": "cancelled",
    }

    orders: list[dict[str, Any]] = []
    processed = 0

    for _, row in orders_df.iterrows():
        if processed >= limit:
            break

        order_id = row["order_id"]
        customer_id = row["customer_id"]

        # Get items for this order
        order_items = items_df[items_df["order_id"] == order_id]
        if order_items.empty:
            continue

        items: list[dict[str, Any]] = []
        total = 0.0

        for _, item_row in order_items.iterrows():
            product_id = item_row["product_id"]
            mapped_product_id = product_id_map.get(product_id)
            if not mapped_product_id:
                # Use deterministic ID even if not in our product set
                mapped_product_id = _deterministic_id(product_id)

            price = float(item_row["price"]) if not pd.isna(item_row["price"]) else 0
            items.append({
                "product_id": mapped_product_id,
                "quantity": 1,
                "price": round(price, 2),
            })
            total += price

        status = status_map.get(row.get("order_status", ""), "pending")
        created_at = row.get("order_purchase_timestamp", "")

        orders.append({
            "id": _deterministic_id(order_id),
            "user_id": _deterministic_id(customer_id),
            "items": items,
            "status": status,
            "total": round(total, 2),
            "created_at": str(created_at) if not pd.isna(created_at) else None,
        })
        processed += 1

    return orders


# ---------------------------------------------------------------------------
# Load into CRUD service
# ---------------------------------------------------------------------------
async def post_entities(
    client: httpx.AsyncClient,
    endpoint: str,
    entities: list[dict[str, Any]],
    label: str,
    batch_size: int = 20,
) -> tuple[int, int]:
    """POST entities to the CRUD service. Returns (success, failed) counts."""
    success = 0
    failed = 0

    for i in tqdm(range(0, len(entities), batch_size), desc=f"Loading {label}"):
        batch = entities[i : i + batch_size]
        tasks = [
            client.post(endpoint, json=entity, timeout=30.0) for entity in batch
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for resp in responses:
            if isinstance(resp, Exception):
                failed += 1
                logger.debug("Request failed: %s", resp)
            elif resp.status_code in (200, 201):
                success += 1
            elif resp.status_code == 409:
                # Already exists — count as success
                success += 1
            else:
                failed += 1
                logger.debug(
                    "HTTP %d: %s", resp.status_code, resp.text[:200]
                )

    return success, failed


async def load_data(
    crud_url: str,
    products: list[dict[str, Any]],
    users: list[dict[str, Any]],
    orders: list[dict[str, Any]],
) -> None:
    """Load all transformed data into the CRUD service."""
    async with httpx.AsyncClient(base_url=crud_url) as client:
        # Verify CRUD service is reachable
        try:
            health = await client.get("/health", timeout=5.0)
            if health.status_code != 200:
                logger.warning("CRUD health check returned %d", health.status_code)
        except httpx.ConnectError:
            logger.error("Cannot connect to CRUD service at %s", crud_url)
            sys.exit(1)

        print(f"\nLoading {len(products)} products...")
        p_ok, p_fail = await post_entities(client, "/products", products, "products")

        print(f"\nLoading {len(users)} users...")
        u_ok, u_fail = await post_entities(client, "/users", users, "users")

        print(f"\nLoading {len(orders)} orders...")
        o_ok, o_fail = await post_entities(client, "/orders", orders, "orders")

        print("\n" + "=" * 50)
        print("Load Summary")
        print("=" * 50)
        print(f"  Products: {p_ok} success, {p_fail} failed (of {len(products)})")
        print(f"  Users:    {u_ok} success, {u_fail} failed (of {len(users)})")
        print(f"  Orders:   {o_ok} success, {o_fail} failed (of {len(orders)})")
        print("=" * 50)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load the Olist Brazilian E-Commerce dataset into the CRUD service.",
        epilog=(
            "Dataset: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce\n"
            "License: CC BY-NC-SA 4.0"
        ),
    )
    parser.add_argument(
        "--crud-url",
        default="http://localhost:8000",
        help="CRUD service base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of products to load (default: 500). "
        "Orders default to 2× this value.",
    )
    parser.add_argument(
        "--order-limit",
        type=int,
        default=None,
        help="Maximum number of orders to load (default: 2× product limit).",
    )
    parser.add_argument(
        "--kaggle-dir",
        type=Path,
        default=Path("./data/olist"),
        help="Directory to download/find the Kaggle dataset.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the dataset from Kaggle (requires kaggle.json credentials).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    print("=" * 60)
    print(" Holiday Peak Hub — Olist Dataset Loader")
    print("=" * 60)
    print(f"  CRUD URL:    {args.crud_url}")
    print(f"  Kaggle Dir:  {args.kaggle_dir}")
    print(f"  Product Limit: {args.limit}")
    print(f"  Order Limit:   {args.order_limit or args.limit * 2}")
    print()
    print("  Dataset: Brazilian E-Commerce (Olist)")
    print("  License: CC BY-NC-SA 4.0")
    print("  Source:  https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
    print("=" * 60)

    # Download or find dataset
    if args.download:
        print("\nDownloading dataset from Kaggle...")
        dataset_path = download_olist_dataset(args.kaggle_dir)
    else:
        dataset_path = find_dataset(args.kaggle_dir)

    print(f"\nDataset path: {dataset_path}")

    # Transform
    print("\nTransforming products...")
    products = transform_products(dataset_path, args.limit)
    print(f"  → {len(products)} products ready")

    # Build product ID mapping for order references
    products_df = pd.read_csv(dataset_path / "olist_products_dataset.csv")
    product_id_map: dict[str, str] = {}
    for _, row in products_df.head(args.limit).iterrows():
        product_id_map[row["product_id"]] = _deterministic_id(row["product_id"])

    print("\nTransforming users...")
    user_limit = min(args.limit * 2, 2000)
    users = transform_users(dataset_path, user_limit)
    print(f"  → {len(users)} users ready")

    print("\nTransforming orders...")
    order_limit = args.order_limit or args.limit * 2
    orders = transform_orders(dataset_path, order_limit, product_id_map)
    print(f"  → {len(orders)} orders ready")

    # Load
    asyncio.run(load_data(args.crud_url, products, users, orders))


if __name__ == "__main__":
    main()
