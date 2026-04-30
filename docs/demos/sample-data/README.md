# Sample Data

**Status**: Phase 1 - Complete

---

## Overview

This directory contains sample datasets for demonstrating agent capabilities, including products, users, orders, reviews, and inventory records.

---

## Datasets

### Products (500 SKUs)
**File**: `products.json`

**Categories** (8):
- Electronics (120 products)
- Apparel (100 products)
- Toys & Games (80 products)
- Home & Garden (70 products)
- Beauty & Personal Care (50 products)
- Sports & Outdoors (40 products)
- Books & Media (30 products)
- Groceries (10 products)

**Fields**:
- SKU, name, description, price, category, brand
- Attributes (color, size, weight, dimensions)
- Images (2-4 per product)
- ACP compliance status

---

### Users (100 Profiles)
**File**: `users.json`

**Roles**:
- Customer (90 users)
- Staff (8 users)
- Admin (2 users)

**Fields**:
- User ID, email, name, role
- Addresses (shipping, billing)
- Purchase history
- Saved payment methods
- Preferences (notifications, language)

---

### Orders (200 Historical)
**File**: `orders.json`

**Status Distribution**:
- Delivered (150 orders)
- In Transit (30 orders)
- Processing (15 orders)
- Cancelled (5 orders)

**Fields**:
- Order ID, user ID, items, totals
- Shipping address, method, carrier
- Status, timestamps (placed, shipped, delivered)
- Payment information

---

### Reviews (300 Product Reviews)
**File**: `reviews.json`

**Rating Distribution**:
- 5 stars: 45% (135 reviews)
- 4 stars: 30% (90 reviews)
- 3 stars: 15% (45 reviews)
- 2 stars: 7% (21 reviews)
- 1 star: 3% (9 reviews)

**Fields**:
- Review ID, product SKU, user ID
- Rating, title, text
- Helpful votes, verified purchase
- Timestamp

---

### Inventory (500 SKUs x 5 Warehouses)
**File**: `inventory.json`

**Warehouses** (5):
- Los Angeles, CA
- New York, NY
- Chicago, IL
- Dallas, TX
- Seattle, WA

**Fields**:
- SKU, warehouse, quantity
- Reserved, available, incoming
- Last updated, reorder point, par level

---

## Loading Sample Data

### Option 1: Bash Script (Linux/macOS/WSL)
```bash
bash load-sample-data.sh
```

### Option 2: PowerShell Script (Windows)
```powershell
.\load-sample-data.ps1
```

### Option 3: Manual (curl)
```bash
# Load products
curl -X POST http://localhost:8000/api/products/bulk \
  -H "Content-Type: application/json" \
  -d @products.json

# Load users
curl -X POST http://localhost:8000/api/users/bulk \
  -H "Content-Type: application/json" \
  -d @users.json

# Load orders
curl -X POST http://localhost:8000/api/orders/bulk \
  -H "Content-Type: application/json" \
  -d @orders.json

# Load reviews
curl -X POST http://localhost:8000/api/reviews/bulk \
  -H "Content-Type: application/json" \
  -d @reviews.json

# Load inventory
curl -X POST http://localhost:8000/api/inventory/bulk \
  -H "Content-Type: application/json" \
  -d @inventory.json
```

---

## Data Generation

### Generate New Sample Data

```bash
# Generate products
python generate-products.py --count 500 --output products.json

# Generate users
python generate-users.py --count 100 --output users.json

# Generate orders
python generate-orders.py --count 200 --users users.json --products products.json --output orders.json

# Generate reviews
python generate-reviews.py --count 300 --users users.json --products products.json --output reviews.json

# Generate inventory
python generate-inventory.py --products products.json --warehouses 5 --output inventory.json
```

---

## Files

- `products.json` - 500 product records
- `users.json` - 100 user profiles
- `orders.json` - 200 order records
- `reviews.json` - 300 product reviews
- `inventory.json` - 2,500 inventory records (500 SKUs x 5 warehouses)
- `load-sample-data.sh` - Bash loading script
- `load-sample-data.ps1` - PowerShell loading script
- `generate-products.py` - Python script to generate products
- `generate-users.py` - Python script to generate users
- `generate-orders.py` - Python script to generate orders
- `generate-reviews.py` - Python script to generate reviews
- `generate-inventory.py` - Python script to generate inventory

---

## Real-World Data — Kaggle Olist (100k orders)

For demos requiring realistic volume and diversity, use the [Kaggle Olist loader](../../../scripts/ops/load-kaggle-olist-dataset.py):

```bash
pip install httpx pandas opendatasets tqdm
python scripts/ops/load-kaggle-olist-dataset.py --download --crud-url http://localhost:8000 --limit 500
```

This downloads the Brazilian E-Commerce dataset (CC BY-NC-SA 4.0), transforms products/users/orders to the CRUD schema, and POSTs them to the service. Use `--limit` to control how many products and `--order-limit` for orders.

---

## Next Steps

1. Load sample data using scripts above or the Kaggle loader
2. Try [API Examples](../api-examples/) (now in [`scripts/demos/`](../../../scripts/demos/))
3. Run [Interactive Scenarios](../interactive-scenarios/)
4. Explore [Jupyter Notebooks](../agent-playgrounds/)
