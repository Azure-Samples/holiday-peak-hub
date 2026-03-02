# Samples Directory

This directory contains sample data and seed scripts for development and testing
of the **Product Truth Layer** (see [Epic #87](https://github.com/Azure-Samples/holiday-peak-hub/issues/87)).

## Directory Structure

```
samples/
├── README.md                       # This file
├── seed_cosmos.py                  # Seed script for Cosmos DB
└── data/
    ├── products_apparel.json       # 12 apparel product styles (varying completeness)
    ├── products_electronics.json   # 12 electronics product styles (varying completeness)
    ├── products_general.json       # 8 general merchandise product styles (varying completeness)
    ├── tenant_config_default.json  # Default tenant configuration
    ├── schemas/
    │   ├── apparel.json            # CategorySchema for apparel
    │   ├── electronics.json        # CategorySchema for electronics
    │   └── general.json            # CategorySchema for general merchandise
    └── mappings/
        └── acp_v1.json             # ACP v1 protocol field mapping
```

## Product Data

Each product file contains an array of product styles. Products are intentionally
created with **varying completeness levels** to exercise the completeness scoring
and enrichment pipeline:

| Category    | Products | Fully Complete | Partially Complete | Minimal Fields |
|-------------|----------|----------------|--------------------|----------------|
| Apparel     | 12       | 6              | 5                  | 1              |
| Electronics | 12       | 5              | 6                  | 1              |
| General     | 8        | 4              | 3                  | 1              |

The `_completeness_note` field in each product entry documents which fields are
present or missing — this metadata is stripped by the seed script before writing
to Cosmos DB.

## Category Schemas

Schemas are defined under `data/schemas/` and follow the `CategorySchema` model.
Each schema specifies:
- **`required_fields`** — fields that must be present for a complete product
- **`optional_fields`** — recommended fields for richer product data
- **`variant_required_fields`** — required fields per variant/SKU
- **`field_definitions`** — type, format, and enum constraints per field

## Seed Script

### Prerequisites

Install the Azure Cosmos DB SDK:

```bash
pip install azure-cosmos
```

Or using `uv`:

```bash
uv pip install azure-cosmos
```

### Usage

#### Local Cosmos Emulator (default)

Start the [Azure Cosmos DB Emulator](https://learn.microsoft.com/azure/cosmos-db/local-emulator)
then run:

```bash
python samples/seed_cosmos.py
```

The script uses the emulator's well-known connection string automatically.

You must create the `truth-store` database with `products` and `schemas` containers
before running the seed script (or use the emulator's Data Explorer).

#### Cloud Cosmos DB

Set the required environment variables and run with `--env cloud`:

```bash
export COSMOS_ACCOUNT_URI="https://<account>.documents.azure.com:443/"
export COSMOS_ACCOUNT_KEY="<your-key>"        # or use managed identity
export COSMOS_DATABASE="truth-store"           # optional, defaults to truth-store
export COSMOS_PRODUCTS_CONTAINER="products"    # optional
export COSMOS_SCHEMAS_CONTAINER="schemas"      # optional

python samples/seed_cosmos.py --env cloud
```

#### Dry Run

Preview what would be written without making any changes:

```bash
python samples/seed_cosmos.py --dry-run
```

#### Seed a Single Category

```bash
python samples/seed_cosmos.py --category apparel
```

#### Seed Schemas Only

```bash
python samples/seed_cosmos.py --schemas-only
```

### What Gets Seeded

| Container    | Documents                                  |
|--------------|--------------------------------------------|
| `schemas`    | 3 category schemas + tenant config + ACP mapping |
| `products`   | 32 product styles across 3 categories       |

All seed operations are **idempotent** — running the script multiple times will
upsert (not duplicate) documents using the `style_id` as the Cosmos DB item `id`.

## ACP Mapping

`data/mappings/acp_v1.json` describes how truth-layer product fields map to
[ACP (Agentic Commerce Protocol)](https://example.com/docs/acp) v1 fields,
including default values and transform rules applied during export.
