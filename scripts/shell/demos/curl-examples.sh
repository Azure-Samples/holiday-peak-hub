#!/usr/bin/env bash
# =============================================================================
# Holiday Peak Hub — API Examples (curl)
# Quick reference for calling each agent service via REST.
# =============================================================================
# Usage:
#   export BASE_URL=http://localhost   # or your APIM gateway URL
#   bash curl-examples.sh
#
# All agents expose POST /invoke accepting JSON payloads.
# CRUD service exposes standard REST endpoints on port 8000.
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"

echo "============================================="
echo " Holiday Peak Hub — curl API Examples"
echo " Base URL: $BASE_URL"
echo "============================================="

# -----------------------------------------------------------------------------
# CRUD Service (Port 8000)
# -----------------------------------------------------------------------------
echo -e "\n--- CRUD Service (Port 8000) ---"

echo -e "\n# List products"
curl -s "$BASE_URL:8000/products?limit=5" | head -c 500
echo

echo -e "\n# Get single product"
curl -s "$BASE_URL:8000/products/d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
echo

echo -e "\n# Create a product"
curl -X POST "$BASE_URL:8000/products" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Noise-Cancelling Headphones",
    "description": "Premium over-ear headphones with active noise cancellation",
    "price": 249.99,
    "category": "Electronics",
    "brand": "AudioTech",
    "features": ["Noise Cancelling", "Bluetooth 5.3", "30h Battery"],
    "tags": ["headphones", "wireless", "anc"]
  }'
echo

echo -e "\n# List orders"
curl -s "$BASE_URL:8000/orders?limit=5" | head -c 500
echo

echo -e "\n# Get user profile"
curl -s "$BASE_URL:8000/users/user-12345"
echo

# =============================================================================
# E-COMMERCE DOMAIN
# =============================================================================
echo -e "\n\n========================================="
echo " E-COMMERCE DOMAIN"
echo "========================================="

# --- Catalog Search (Port 8001) ---
echo -e "\n--- ecommerce-catalog-search (Port 8001) ---"
curl -X POST "$BASE_URL:8001/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "wireless headphones under $100",
    "filters": {"category": "Electronics", "price_max": 100},
    "limit": 10,
    "mode": "intelligent"
  }'
echo

# --- Product Detail Enrichment (Port 8002) ---
echo -e "\n--- ecommerce-product-detail-enrichment (Port 8002) ---"
curl -X POST "$BASE_URL:8002/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "related_limit": 4
  }'
echo

# --- Cart Intelligence (Port 8003) ---
echo -e "\n--- ecommerce-cart-intelligence (Port 8003) ---"
curl -X POST "$BASE_URL:8003/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-12345",
    "action": "add_item",
    "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "quantity": 1
  }'
echo

# --- Checkout Support (Port 8004) ---
echo -e "\n--- ecommerce-checkout-support (Port 8004) ---"
curl -X POST "$BASE_URL:8004/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "cart_id": "cart-12345",
    "user_id": "user-12345",
    "shipping_address": {"zip": "90210", "country": "US"}
  }'
echo

# --- Order Status (Port 8005) ---
echo -e "\n--- ecommerce-order-status (Port 8005) ---"
curl -X POST "$BASE_URL:8005/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-67890",
    "user_id": "user-12345"
  }'
echo

# =============================================================================
# PRODUCT MANAGEMENT DOMAIN
# =============================================================================
echo -e "\n\n========================================="
echo " PRODUCT MANAGEMENT DOMAIN"
echo "========================================="

# --- Normalization & Classification (Port 8006) ---
echo -e "\n--- product-management-normalization-classification (Port 8006) ---"
curl -X POST "$BASE_URL:8006/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "product_data": {
      "vendor_sku": "VEND-XYZ-789",
      "name": "wireless headset - bluetooth 5.0",
      "category": "audio equipment",
      "attributes": {"color": "black", "weight": "250g"}
    },
    "target_taxonomy": "retail_standard_v2"
  }'
echo

# --- ACP Transformation (Port 8007) ---
echo -e "\n--- product-management-acp-transformation (Port 8007) ---"
curl -X POST "$BASE_URL:8007/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "include_sections": ["description", "features", "specifications", "media"]
  }'
echo

# --- Consistency Validation (Port 8008) ---
echo -e "\n--- product-management-consistency-validation (Port 8008) ---"
curl -X POST "$BASE_URL:8008/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "validation_rules": ["required_fields", "image_quality", "description_length", "acp_compliance"]
  }'
echo

# --- Assortment Optimization (Port 8009) ---
echo -e "\n--- product-management-assortment-optimization (Port 8009) ---"
curl -X POST "$BASE_URL:8009/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "Electronics > Audio > Headphones",
    "new_sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "optimization_goal": "maximize_category_conversion"
  }'
echo

# =============================================================================
# CRM DOMAIN
# =============================================================================
echo -e "\n\n========================================="
echo " CRM DOMAIN"
echo "========================================="

# --- Profile Aggregation (Port 8010) ---
echo -e "\n--- crm-profile-aggregation (Port 8010) ---"
curl -X POST "$BASE_URL:8010/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-12345",
    "include_sources": ["orders", "browsing", "support_tickets", "reviews"]
  }'
echo

# --- Segmentation & Personalization (Port 8011) ---
echo -e "\n--- crm-segmentation-personalization (Port 8011) ---"
curl -X POST "$BASE_URL:8011/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-12345",
    "segmentation_model": "rfm_enhanced",
    "personalization_context": "homepage"
  }'
echo

# --- Campaign Intelligence (Port 8012) ---
echo -e "\n--- crm-campaign-intelligence (Port 8012) ---"
curl -X POST "$BASE_URL:8012/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_type": "holiday_promotion",
    "target_segment": "high_value_electronics",
    "budget": 5000,
    "channel": "email"
  }'
echo

# --- Support Assistance (Port 8013) ---
echo -e "\n--- crm-support-assistance (Port 8013) ---"
curl -X POST "$BASE_URL:8013/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-54321",
    "user_id": "user-12345",
    "query": "My order has not arrived yet and the tracking shows no updates for 3 days"
  }'
echo

# =============================================================================
# INVENTORY DOMAIN
# =============================================================================
echo -e "\n\n========================================="
echo " INVENTORY DOMAIN"
echo "========================================="

# --- Health Check (Port 8014) ---
echo -e "\n--- inventory-health-check (Port 8014) ---"
curl -X POST "$BASE_URL:8014/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "warehouse_id": "WH-LAX-01",
    "categories": ["Electronics", "Home & Kitchen"],
    "threshold": "critical"
  }'
echo

# --- JIT Replenishment (Port 8015) ---
echo -e "\n--- inventory-jit-replenishment (Port 8015) ---"
curl -X POST "$BASE_URL:8015/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "current_stock": 8,
    "daily_velocity": 15,
    "lead_time_days": 3
  }'
echo

# --- Reservation Validation (Port 8016) ---
echo -e "\n--- inventory-reservation-validation (Port 8016) ---"
curl -X POST "$BASE_URL:8016/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "quantity": 1,
    "order_id": "ORD-67890",
    "warehouse_preference": "closest"
  }'
echo

# --- Alerts & Triggers (Port 8017) ---
echo -e "\n--- inventory-alerts-triggers (Port 8017) ---"
curl -X POST "$BASE_URL:8017/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_type": "stock_below_threshold",
    "warehouse_id": "WH-LAX-01",
    "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "current_level": 5,
    "threshold": 20
  }'
echo

# =============================================================================
# LOGISTICS DOMAIN
# =============================================================================
echo -e "\n\n========================================="
echo " LOGISTICS DOMAIN"
echo "========================================="

# --- Carrier Selection (Port 8018) ---
echo -e "\n--- logistics-carrier-selection (Port 8018) ---"
curl -X POST "$BASE_URL:8018/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-67890",
    "origin_zip": "90001",
    "destination_zip": "90210",
    "weight_lbs": 1.2,
    "dimensions": {"length": 10, "width": 8, "height": 4},
    "speed_preference": "2-day"
  }'
echo

# --- ETA Computation (Port 8019) ---
echo -e "\n--- logistics-eta-computation (Port 8019) ---"
curl -X POST "$BASE_URL:8019/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-67890",
    "shipment_id": "SHIP-11111",
    "carrier": "UPS",
    "service_level": "2nd_day_air",
    "origin_zip": "90001",
    "destination_zip": "90210"
  }'
echo

# --- Route Issue Detection (Port 8020) ---
echo -e "\n--- logistics-route-issue-detection (Port 8020) ---"
curl -X POST "$BASE_URL:8020/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "SHIP-11111",
    "carrier": "UPS",
    "tracking_number": "1Z999AA1012345678",
    "expected_delivery": "2026-05-02"
  }'
echo

# --- Returns Support (Port 8021) ---
echo -e "\n--- logistics-returns-support (Port 8021) ---"
curl -X POST "$BASE_URL:8021/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-67890",
    "user_id": "user-12345",
    "reason": "Product does not match description",
    "items": [{"sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462", "quantity": 1}]
  }'
echo

# =============================================================================
# SEARCH & TRUTH PIPELINE
# =============================================================================
echo -e "\n\n========================================="
echo " SEARCH & TRUTH PIPELINE"
echo "========================================="

# --- Search Enrichment Agent (Port 8022) ---
echo -e "\n--- search-enrichment-agent (Port 8022) ---"
curl -X POST "$BASE_URL:8022/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "comfortable noise cancelling headphones for long flights",
    "index": "products",
    "top_k": 5,
    "search_mode": "hybrid"
  }'
echo

# --- Truth Ingestion (Port 8023) ---
echo -e "\n--- truth-ingestion (Port 8023) ---"
curl -X POST "$BASE_URL:8023/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "crud_export",
    "entity_type": "products",
    "batch_id": "BATCH-2026-04-30",
    "options": {"validate_schema": true, "deduplicate": true}
  }'
echo

# --- Truth Enrichment (Port 8024) ---
echo -e "\n--- truth-enrichment (Port 8024) ---"
curl -X POST "$BASE_URL:8024/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "BATCH-2026-04-30",
    "enrichment_pipelines": ["ucp", "acp"],
    "entity_type": "products"
  }'
echo

# --- Truth HITL (Port 8025) ---
echo -e "\n--- truth-hitl (Port 8025) ---"
curl -X POST "$BASE_URL:8025/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "BATCH-2026-04-30",
    "review_queue": "pending",
    "action": "list",
    "limit": 10
  }'
echo

# --- Truth Export (Port 8026) ---
echo -e "\n--- truth-export (Port 8026) ---"
curl -X POST "$BASE_URL:8026/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "BATCH-2026-04-30",
    "target": "ai_search",
    "format": "json",
    "include_vectors": true
  }'
echo

echo -e "\n\n============================================="
echo " All examples completed."
echo "============================================="
