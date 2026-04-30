# =============================================================================
# Holiday Peak Hub — API Examples (PowerShell)
# Quick reference for calling each agent service via REST.
# =============================================================================
# Usage:
#   $env:BASE_URL = "http://localhost"   # or your APIM gateway URL
#   .\powershell-examples.ps1
#
# All agents expose POST /invoke accepting JSON payloads.
# CRUD service exposes standard REST endpoints on port 8000.
# =============================================================================

$ErrorActionPreference = "Stop"

$BaseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost" }

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Holiday Peak Hub — PowerShell API Examples"
Write-Host " Base URL: $BaseUrl"
Write-Host "=============================================" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# CRUD Service (Port 8000)
# -----------------------------------------------------------------------------
Write-Host "`n--- CRUD Service (Port 8000) ---" -ForegroundColor Yellow

Write-Host "`n# List products"
Invoke-RestMethod -Uri "$BaseUrl`:8000/products?limit=5" -Method Get | ConvertTo-Json -Depth 5

Write-Host "`n# Get single product"
Invoke-RestMethod -Uri "$BaseUrl`:8000/products/d9c3b1de-7158-5ea1-9f33-7bdaec2f0462" -Method Get | ConvertTo-Json -Depth 5

Write-Host "`n# Create a product"
$productBody = @{
    name        = "Wireless Noise-Cancelling Headphones"
    description = "Premium over-ear headphones with active noise cancellation"
    price       = 249.99
    category    = "Electronics"
    brand       = "AudioTech"
    features    = @("Noise Cancelling", "Bluetooth 5.3", "30h Battery")
    tags        = @("headphones", "wireless", "anc")
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8000/products" -Method Post -Body $productBody -ContentType "application/json"

Write-Host "`n# List orders"
Invoke-RestMethod -Uri "$BaseUrl`:8000/orders?limit=5" -Method Get | ConvertTo-Json -Depth 5

Write-Host "`n# Get user profile"
Invoke-RestMethod -Uri "$BaseUrl`:8000/users/user-12345" -Method Get | ConvertTo-Json -Depth 5

# =============================================================================
# E-COMMERCE DOMAIN
# =============================================================================
Write-Host "`n`n=========================================" -ForegroundColor Green
Write-Host " E-COMMERCE DOMAIN" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# --- Catalog Search (Port 8001) ---
Write-Host "`n--- ecommerce-catalog-search (Port 8001) ---" -ForegroundColor Yellow
$body = @{
    query   = "wireless headphones under `$100"
    filters = @{ category = "Electronics"; price_max = 100 }
    limit   = 10
    mode    = "intelligent"
} | ConvertTo-Json -Depth 3
Invoke-RestMethod -Uri "$BaseUrl`:8001/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Product Detail Enrichment (Port 8002) ---
Write-Host "`n--- ecommerce-product-detail-enrichment (Port 8002) ---" -ForegroundColor Yellow
$body = @{
    sku           = "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
    related_limit = 4
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8002/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Cart Intelligence (Port 8003) ---
Write-Host "`n--- ecommerce-cart-intelligence (Port 8003) ---" -ForegroundColor Yellow
$body = @{
    user_id  = "user-12345"
    action   = "add_item"
    sku      = "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
    quantity = 1
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8003/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Checkout Support (Port 8004) ---
Write-Host "`n--- ecommerce-checkout-support (Port 8004) ---" -ForegroundColor Yellow
$body = @{
    cart_id          = "cart-12345"
    user_id          = "user-12345"
    shipping_address = @{ zip = "90210"; country = "US" }
} | ConvertTo-Json -Depth 3
Invoke-RestMethod -Uri "$BaseUrl`:8004/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Order Status (Port 8005) ---
Write-Host "`n--- ecommerce-order-status (Port 8005) ---" -ForegroundColor Yellow
$body = @{
    order_id = "ORD-67890"
    user_id  = "user-12345"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8005/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# =============================================================================
# PRODUCT MANAGEMENT DOMAIN
# =============================================================================
Write-Host "`n`n=========================================" -ForegroundColor Green
Write-Host " PRODUCT MANAGEMENT DOMAIN" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# --- Normalization & Classification (Port 8006) ---
Write-Host "`n--- product-management-normalization-classification (Port 8006) ---" -ForegroundColor Yellow
$body = @{
    product_data    = @{
        vendor_sku = "VEND-XYZ-789"
        name       = "wireless headset - bluetooth 5.0"
        category   = "audio equipment"
        attributes = @{ color = "black"; weight = "250g" }
    }
    target_taxonomy = "retail_standard_v2"
} | ConvertTo-Json -Depth 4
Invoke-RestMethod -Uri "$BaseUrl`:8006/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- ACP Transformation (Port 8007) ---
Write-Host "`n--- product-management-acp-transformation (Port 8007) ---" -ForegroundColor Yellow
$body = @{
    sku              = "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
    include_sections = @("description", "features", "specifications", "media")
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8007/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Consistency Validation (Port 8008) ---
Write-Host "`n--- product-management-consistency-validation (Port 8008) ---" -ForegroundColor Yellow
$body = @{
    sku              = "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
    validation_rules = @("required_fields", "image_quality", "description_length", "acp_compliance")
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8008/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Assortment Optimization (Port 8009) ---
Write-Host "`n--- product-management-assortment-optimization (Port 8009) ---" -ForegroundColor Yellow
$body = @{
    category          = "Electronics > Audio > Headphones"
    new_sku           = "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
    optimization_goal = "maximize_category_conversion"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8009/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# =============================================================================
# CRM DOMAIN
# =============================================================================
Write-Host "`n`n=========================================" -ForegroundColor Green
Write-Host " CRM DOMAIN" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# --- Profile Aggregation (Port 8010) ---
Write-Host "`n--- crm-profile-aggregation (Port 8010) ---" -ForegroundColor Yellow
$body = @{
    user_id         = "user-12345"
    include_sources = @("orders", "browsing", "support_tickets", "reviews")
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8010/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Segmentation & Personalization (Port 8011) ---
Write-Host "`n--- crm-segmentation-personalization (Port 8011) ---" -ForegroundColor Yellow
$body = @{
    user_id                 = "user-12345"
    segmentation_model      = "rfm_enhanced"
    personalization_context = "homepage"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8011/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Campaign Intelligence (Port 8012) ---
Write-Host "`n--- crm-campaign-intelligence (Port 8012) ---" -ForegroundColor Yellow
$body = @{
    campaign_type  = "holiday_promotion"
    target_segment = "high_value_electronics"
    budget         = 5000
    channel        = "email"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8012/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Support Assistance (Port 8013) ---
Write-Host "`n--- crm-support-assistance (Port 8013) ---" -ForegroundColor Yellow
$body = @{
    ticket_id = "TKT-54321"
    user_id   = "user-12345"
    query     = "My order has not arrived yet and the tracking shows no updates for 3 days"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8013/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# =============================================================================
# INVENTORY DOMAIN
# =============================================================================
Write-Host "`n`n=========================================" -ForegroundColor Green
Write-Host " INVENTORY DOMAIN" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# --- Health Check (Port 8014) ---
Write-Host "`n--- inventory-health-check (Port 8014) ---" -ForegroundColor Yellow
$body = @{
    warehouse_id = "WH-LAX-01"
    categories   = @("Electronics", "Home & Kitchen")
    threshold    = "critical"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8014/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- JIT Replenishment (Port 8015) ---
Write-Host "`n--- inventory-jit-replenishment (Port 8015) ---" -ForegroundColor Yellow
$body = @{
    sku            = "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
    current_stock  = 8
    daily_velocity = 15
    lead_time_days = 3
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8015/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Reservation Validation (Port 8016) ---
Write-Host "`n--- inventory-reservation-validation (Port 8016) ---" -ForegroundColor Yellow
$body = @{
    sku                  = "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
    quantity             = 1
    order_id             = "ORD-67890"
    warehouse_preference = "closest"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8016/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Alerts & Triggers (Port 8017) ---
Write-Host "`n--- inventory-alerts-triggers (Port 8017) ---" -ForegroundColor Yellow
$body = @{
    alert_type    = "stock_below_threshold"
    warehouse_id  = "WH-LAX-01"
    sku           = "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
    current_level = 5
    threshold     = 20
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8017/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# =============================================================================
# LOGISTICS DOMAIN
# =============================================================================
Write-Host "`n`n=========================================" -ForegroundColor Green
Write-Host " LOGISTICS DOMAIN" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# --- Carrier Selection (Port 8018) ---
Write-Host "`n--- logistics-carrier-selection (Port 8018) ---" -ForegroundColor Yellow
$body = @{
    order_id         = "ORD-67890"
    origin_zip       = "90001"
    destination_zip  = "90210"
    weight_lbs       = 1.2
    dimensions       = @{ length = 10; width = 8; height = 4 }
    speed_preference = "2-day"
} | ConvertTo-Json -Depth 3
Invoke-RestMethod -Uri "$BaseUrl`:8018/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- ETA Computation (Port 8019) ---
Write-Host "`n--- logistics-eta-computation (Port 8019) ---" -ForegroundColor Yellow
$body = @{
    order_id       = "ORD-67890"
    shipment_id    = "SHIP-11111"
    carrier        = "UPS"
    service_level  = "2nd_day_air"
    origin_zip     = "90001"
    destination_zip = "90210"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8019/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Route Issue Detection (Port 8020) ---
Write-Host "`n--- logistics-route-issue-detection (Port 8020) ---" -ForegroundColor Yellow
$body = @{
    shipment_id       = "SHIP-11111"
    carrier           = "UPS"
    tracking_number   = "1Z999AA1012345678"
    expected_delivery = "2026-05-02"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8020/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Returns Support (Port 8021) ---
Write-Host "`n--- logistics-returns-support (Port 8021) ---" -ForegroundColor Yellow
$body = @{
    order_id = "ORD-67890"
    user_id  = "user-12345"
    reason   = "Product does not match description"
    items    = @(@{ sku = "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"; quantity = 1 })
} | ConvertTo-Json -Depth 3
Invoke-RestMethod -Uri "$BaseUrl`:8021/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# =============================================================================
# SEARCH & TRUTH PIPELINE
# =============================================================================
Write-Host "`n`n=========================================" -ForegroundColor Green
Write-Host " SEARCH & TRUTH PIPELINE" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# --- Search Enrichment Agent (Port 8022) ---
Write-Host "`n--- search-enrichment-agent (Port 8022) ---" -ForegroundColor Yellow
$body = @{
    query       = "comfortable noise cancelling headphones for long flights"
    index       = "products"
    top_k       = 5
    search_mode = "hybrid"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8022/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Truth Ingestion (Port 8023) ---
Write-Host "`n--- truth-ingestion (Port 8023) ---" -ForegroundColor Yellow
$body = @{
    source      = "crud_export"
    entity_type = "products"
    batch_id    = "BATCH-2026-04-30"
    options     = @{ validate_schema = $true; deduplicate = $true }
} | ConvertTo-Json -Depth 3
Invoke-RestMethod -Uri "$BaseUrl`:8023/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Truth Enrichment (Port 8024) ---
Write-Host "`n--- truth-enrichment (Port 8024) ---" -ForegroundColor Yellow
$body = @{
    batch_id             = "BATCH-2026-04-30"
    enrichment_pipelines = @("ucp", "acp")
    entity_type          = "products"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8024/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Truth HITL (Port 8025) ---
Write-Host "`n--- truth-hitl (Port 8025) ---" -ForegroundColor Yellow
$body = @{
    batch_id     = "BATCH-2026-04-30"
    review_queue = "pending"
    action       = "list"
    limit        = 10
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8025/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# --- Truth Export (Port 8026) ---
Write-Host "`n--- truth-export (Port 8026) ---" -ForegroundColor Yellow
$body = @{
    batch_id        = "BATCH-2026-04-30"
    target          = "ai_search"
    format          = "json"
    include_vectors = $true
} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl`:8026/invoke" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

Write-Host "`n`n=============================================" -ForegroundColor Cyan
Write-Host " All examples completed." -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
