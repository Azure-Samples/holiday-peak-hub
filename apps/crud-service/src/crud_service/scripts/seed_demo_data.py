"""Seed demo data into CRUD PostgreSQL tables.

This script is intended for demonstration environments and runs inside AKS,
using the same PostgreSQL environment variables configured for the CRUD service.
"""

import asyncio
import json
import os
import random
from datetime import UTC, datetime

import asyncpg
from faker import Faker


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _build_dsn() -> str:
    postgres_host = _required_env("POSTGRES_HOST")
    postgres_user = _required_env("POSTGRES_USER")
    postgres_password = _required_env("POSTGRES_PASSWORD")
    postgres_database = os.getenv("POSTGRES_DATABASE", "holiday_peak_crud")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_ssl = os.getenv("POSTGRES_SSL", "true").lower() == "true"
    sslmode = "require" if postgres_ssl else "disable"

    return (
        f"postgresql://{postgres_user}:{postgres_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_database}?sslmode={sslmode}"
    )


async def _ensure_table(conn: asyncpg.Connection, table_name: str) -> None:
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id TEXT PRIMARY KEY,
            partition_key TEXT,
            data JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """)
    await conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_partition_key ON {table_name}(partition_key)"
    )
    await conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_data_gin ON {table_name} USING GIN (data)"
    )


async def _upsert_item(
    conn: asyncpg.Connection,
    table_name: str,
    item_id: str,
    partition_key: str,
    item: dict,
) -> None:
    await conn.execute(
        f"""
        INSERT INTO {table_name} (id, partition_key, data, created_at, updated_at)
        VALUES ($1, $2, $3::jsonb, NOW(), NOW())
        ON CONFLICT (id)
        DO UPDATE SET
            partition_key = EXCLUDED.partition_key,
            data = EXCLUDED.data,
            updated_at = NOW()
        """,
        item_id,
        partition_key,
        json.dumps(item),
    )


async def main() -> None:
    seed = int(os.getenv("DEMO_SEED_RANDOM", "42"))
    categories_count = int(os.getenv("DEMO_SEED_CATEGORIES", "10"))
    products_count = int(os.getenv("DEMO_SEED_PRODUCTS", "100"))
    environment = os.getenv("DEMO_ENVIRONMENT", "dev")

    random.seed(seed)
    fake = Faker()
    Faker.seed(seed)

    dsn = _build_dsn()
    conn = await asyncpg.connect(dsn)

    try:
        await _ensure_table(conn, "categories")
        await _ensure_table(conn, "products")

        now = datetime.now(UTC).isoformat()

        category_ids: list[str] = []
        for index in range(1, categories_count + 1):
            category_id = f"demo-cat-{index:03d}"
            category_ids.append(category_id)

            category = {
                "id": category_id,
                "name": f"{fake.word().title()} {fake.word().title()}",
                "description": fake.sentence(nb_words=10),
                "image_url": f"https://picsum.photos/seed/{category_id}/800/600",
                "seeded": True,
                "environment": environment,
                "updated_at": now,
            }

            await _upsert_item(
                conn=conn,
                table_name="categories",
                item_id=category_id,
                partition_key=category_id,
                item=category,
            )

        for index in range(1, products_count + 1):
            product_id = f"demo-prd-{index:04d}"
            category_id = random.choice(category_ids)
            price = round(random.uniform(9.9, 399.9), 2)

            product = {
                "id": product_id,
                "name": f"{fake.color_name()} {fake.word().title()} {fake.word().title()}",
                "description": fake.paragraph(nb_sentences=2),
                "price": price,
                "category_id": category_id,
                "image_url": f"https://picsum.photos/seed/{product_id}/800/600",
                "in_stock": random.choice([True, True, True, False]),
                "rating": round(random.uniform(3.4, 5.0), 1),
                "review_count": random.randint(5, 500),
                "features": [fake.word().title() for _ in range(3)],
                "seeded": True,
                "environment": environment,
                "updated_at": now,
            }

            await _upsert_item(
                conn=conn,
                table_name="products",
                item_id=product_id,
                partition_key=category_id,
                item=product,
            )

        print(
            f"Seed completed for environment={environment}: "
            f"categories={categories_count}, products={products_count}"
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
