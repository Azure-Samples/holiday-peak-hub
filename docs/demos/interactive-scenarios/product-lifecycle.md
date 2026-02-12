# Product Lifecycle Demo

**Scenario**: Product Ingestion → Normalization → Enrichment → Quality Check → Optimization  
**Duration**: 20-25 minutes  
**Agents Involved**: 5  
**Status**: Phase 3 - Planned

---

## Overview

This scenario demonstrates the complete product data management lifecycle, from raw product ingestion through automated normalization, ACP compliance, quality validation, and assortment optimization.

---

## Scenario Flow

### Step 1: Raw Product Ingestion
**Initial Data** (from vendor feed):
```json
{
  "vendor_sku": "VEND-XYZ-789",
  "name": "wireless headset - bluetooth 5.0",
  "desc": "Great headphones with noise cancelling",
  "price": "$99.99",
  "category": "audio equipment",
  "attributes": {
    "color": "black",
    "weight": "250g"
  },
  "images": ["http://vendor.com/img1.jpg"]
}
```

**Issues with Raw Data**:
- Inconsistent naming convention
- Non-standard category taxonomy
- Unstructured attributes
- External image URLs (not CDN-optimized)
- Missing required fields (brand, UPC, dimensions)

---

### Step 2: Normalization & Classification
**Agent**: `product-management-normalization-classification` (Port 8006)  
**Goal**: Standardize taxonomy and extract structured attributes

**Request**:
```json
POST http://localhost:8006/invoke
{
  "product_data": {
    "vendor_sku": "VEND-XYZ-789",
    "name": "wireless headset - bluetooth 5.0",
    "category": "audio equipment",
    "attributes": {"color": "black", "weight": "250g"}
  },
  "target_taxonomy": "retail_standard_v2"
}
```

**Expected Output**:
```json
{
  "normalized_product": {
    "sku": "ELEC-HEADPHONE-015",
    "name": "Wireless Bluetooth 5.0 Headset",
    "category": {
      "l1": "Electronics",
      "l2": "Audio",
      "l3": "Headphones",
      "l4": "Wireless"
    },
    "attributes": {
      "color": "Black",
      "weight_oz": 8.8,
      "connectivity": "Bluetooth 5.0",
      "features": ["Noise Cancelling"]
    }
  },
  "confidence_score": 0.92,
  "changes_made": [
    "Standardized category taxonomy (audio equipment → Electronics > Audio > Headphones > Wireless)",
    "Normalized name format",
    "Converted weight units (250g → 8.8oz)",
    "Extracted connectivity standard"
  ]
}
```

**Memory Usage**:
- Warm (Cosmos): Taxonomy mappings cache
- Warm (Cosmos): Vendor-specific rules

**SLM vs LLM**:
- **SLM** handles standard normalization (80% of cases)
- **LLM** escalates for ambiguous categories or complex attribute extraction

---

### Step 3: ACP Transformation
**Agent**: `product-management-acp-transformation` (Port 8007)  
**Goal**: Generate Agentic Commerce Protocol (ACP) compliant metadata

**Request**:
```json
POST http://localhost:8007/invoke
{
  "sku": "ELEC-HEADPHONE-015",
  "include_sections": ["description", "features", "specifications", "media"]
}
```

**Expected Output**:
```json
{
  "acp_content": {
    "short_description": "Premium wireless headphones with Bluetooth 5.0 and active noise cancellation.",
    "long_description": "Experience superior audio quality with our Bluetooth 5.0 wireless headphones. Featuring active noise cancellation technology, these headphones deliver immersive sound while blocking out ambient noise. The comfortable over-ear design ensures all-day wearability, while the 30-hour battery life keeps you connected through long flights or commutes.",
    "feature_list": [
      "Bluetooth 5.0 connectivity for stable wireless connection",
      "Active Noise Cancellation (ANC) technology",
      "30-hour battery life on a single charge",
      "Comfortable over-ear design with memory foam cushions",
      "Built-in microphone for hands-free calls",
      "Foldable design for easy portability"
    ],
    "specifications": {
      "connectivity": "Bluetooth 5.0",
      "battery_life": "30 hours",
      "charging_time": "2 hours",
      "weight": "8.8 oz (250g)",
      "color_options": ["Black", "Silver", "Navy Blue"],
      "warranty": "1 year manufacturer warranty"
    },
    "media": {
      "images": [
        {
          "url": "https://cdn.retailer.com/products/ELEC-HEADPHONE-015/main.jpg",
          "alt": "Wireless Bluetooth 5.0 Headset - Front View",
          "type": "primary"
        },
        {
          "url": "https://cdn.retailer.com/products/ELEC-HEADPHONE-015/side.jpg",
          "alt": "Wireless Bluetooth 5.0 Headset - Side Profile",
          "type": "alternate"
        }
      ],
      "videos": [
        {
          "url": "https://cdn.retailer.com/products/ELEC-HEADPHONE-015/demo.mp4",
          "title": "Product Demo - Noise Cancellation Feature"
        }
      ]
    }
  },
  "acp_version": "1.2",
  "completeness_score": 0.85
}
```

**MCP Tool Calls** (internal):
- `/mcp/generate_seo_keywords` → SEO optimization
- `/mcp/get_competitor_content` → Content benchmarking
- `/mcp/optimize_images` → CDN migration and optimization

**Memory Usage**:
- Warm (Cosmos): Generated ACP content (6-month retention)
- Cold (Blob): Media assets (permanent)

**SLM vs LLM**:
- **LLM** required for high-quality content generation
- Token usage: ~3,500 tokens per product

---

### Step 4: Product Detail Enrichment
**Agent**: `ecommerce-product-detail-enrichment` (Port 8002)  
**Goal**: Merge ACP content with catalog data for PDP

**Request**:
```json
POST http://localhost:8002/invoke
{
  "sku": "ELEC-HEADPHONE-015",
  "related_limit": 4
}
```

**Expected Output**:
```json
{
  "enriched_product": {
    "sku": "ELEC-HEADPHONE-015",
    "name": "Wireless Bluetooth 5.0 Headset",
    "price": 99.99,
    "acp_content": { /* from Step 3 */ },
    "reviews": {
      "average_rating": 4.6,
      "review_count": 128,
      "highlights": ["Great sound quality", "Comfortable", "Battery lasts forever"]
    },
    "inventory": {
      "status": "in_stock",
      "quantity": 45,
      "warehouses": ["Los Angeles", "New York", "Chicago"]
    },
    "related_products": [
      {"sku": "ELEC-CASE-001", "name": "Premium Headphone Case"},
      {"sku": "ELEC-CABLE-005", "name": "USB-C Charging Cable"},
      {"sku": "ELEC-HEADPHONE-016", "name": "Pro Wireless Headset (Upgrade)"}
    ]
  }
}
```

**Memory Usage**:
- Hot (Redis): PDP cache (5 min TTL)
- Warm (Cosmos): Enrichment metadata

---

### Step 5: Consistency Validation
**Agent**: `product-management-consistency-validation` (Port 8008)  
**Goal**: Quality check and completeness scoring

**Request**:
```json
POST http://localhost:8008/invoke
{
  "sku": "ELEC-HEADPHONE-015",
  "validation_rules": ["required_fields", "image_quality", "description_length", "acp_compliance"]
}
```

**Expected Output**:
```json
{
  "validation_report": {
    "overall_score": 0.85,
    "status": "pass_with_warnings",
    "checks": [
      {
        "rule": "required_fields",
        "status": "pass",
        "score": 1.0,
        "details": "All required fields present: name, SKU, price, category, description"
      },
      {
        "rule": "image_quality",
        "status": "pass",
        "score": 0.9,
        "details": "2 high-quality images (1200x1200px), 1 video. Recommended: Add 2 more alternate views."
      },
      {
        "rule": "description_length",
        "status": "warning",
        "score": 0.7,
        "details": "Long description is 280 characters. Recommended: 350-500 characters for better SEO."
      },
      {
        "rule": "acp_compliance",
        "status": "pass",
        "score": 0.95,
        "details": "ACP v1.2 compliant. Minor: Add sustainability information for higher score."
      }
    ],
    "recommendations": [
      "Add 2 more product images (lifestyle shots recommended)",
      "Expand long description to 350-500 characters",
      "Include sustainability certifications if applicable"
    ]
  }
}
```

**Event Published**:
- Topic: `product-events`
- Event: `validation_completed`
- Payload: `{"sku": "...", "score": 0.85, "status": "pass_with_warnings"}`

**Memory Usage**:
- Warm (Cosmos): Validation history
- Cold (Blob): Detailed validation reports (long-term analytics)

---

### Step 6: Assortment Optimization
**Agent**: `product-management-assortment-optimization` (Port 8009)  
**Goal**: Determine category placement and merchandising strategy

**Request**:
```json
POST http://localhost:8009/invoke
{
  "category": "Electronics > Audio > Headphones",
  "new_sku": "ELEC-HEADPHONE-015",
  "optimization_goal": "maximize_category_conversion"
}
```

**Expected Output**:
```json
{
  "optimization_recommendation": {
    "placement": {
      "homepage_featured": false,
      "category_featured": true,
      "cross_sell_groups": ["ELEC-CASE-001", "ELEC-CABLE-005"],
      "bundle_opportunities": [
        {
          "bundle_skus": ["ELEC-HEADPHONE-015", "ELEC-CASE-001"],
          "bundle_price": 119.99,
          "expected_lift": "18% increase in AOV"
        }
      ]
    },
    "pricing_strategy": {
      "current_price": 99.99,
      "competitor_range": [89.99, 129.99],
      "recommended_position": "mid-tier",
      "promo_eligibility": true,
      "suggested_promo": "10% off for email subscribers"
    },
    "inventory_targets": {
      "par_level": 50,
      "max_level": 200,
      "reorder_point": 20,
      "forecasted_demand": "15 units/day"
    },
    "market_insights": {
      "category_growth": "+12% YoY",
      "competitive_intensity": "high",
      "seasonality": "Peak: Q4 (holiday), Low: Q2"
    }
  }
}
```

**MCP Tool Calls** (internal):
- `/mcp/get_category_performance` → Historical sales data
- `/mcp/get_competitor_analysis` → Price intelligence
- `/mcp/get_demand_forecast` → ML-based demand prediction

**Memory Usage**:
- Warm (Cosmos): Category performance metrics
- Cold (Blob): Historical assortment data

**SLM vs LLM**:
- **LLM** required for complex optimization logic
- Token usage: ~4,000 tokens per analysis

---

## Event Choreography

### End-to-End Event Flow
```
[Raw Product Ingested] → product-events.product_created
   ↓
[Normalization Agent] → product-events.product_normalized
   ↓
[ACP Transformation Agent] → product-events.acp_generated
   ↓
[Enrichment Agent] → product-events.product_enriched
   ↓
[Validation Agent] → product-events.validation_completed
   ↓
[Assortment Optimization Agent] → product-events.optimization_completed
   ↓
[Product Live on Site]
```

### Asynchronous Processing
- **Step 1-2**: Synchronous (user waits for normalization)
- **Step 3-6**: Asynchronous (background processing via Event Hubs)
- **Time to Live**: ~5-10 minutes for full lifecycle

---

## Performance Metrics

### Processing Time Breakdown
- **Normalization**: 150ms (SLM)
- **ACP Transformation**: 800ms (LLM, content generation)
- **Enrichment**: 120ms (parallel adapter calls)
- **Validation**: 200ms (SLM, rule-based checks)
- **Optimization**: 600ms (LLM, complex analysis)

**Total Processing Time**: ~1,870ms (~1.9 seconds)

### Quality Improvements

| Metric | Before Agents | After Agents | Improvement |
|--------|---------------|--------------|-------------|
| Category Accuracy | 65% | 94% | +29 percentage points |
| Description Quality | Low (vendor copy) | High (ACP-compliant) | Qualitative improvement |
| Image Completeness | 1.2 images/product | 3.5 images/product | +192% |
| PDP Conversion Rate | 2.1% | 3.4% | +62% |
| Time to Publish | 2-3 days (manual) | < 10 minutes (automated) | -99% |

---

## Data Quality Dashboard

### Before Agent Processing
```
Product: VEND-XYZ-789
Completeness Score: 35/100
Issues:
  ❌ Category: Non-standard taxonomy
  ❌ Name: Inconsistent format
  ❌ Description: Poor quality (25 words)
  ❌ Images: 1 low-res image (external URL)
  ❌ Attributes: Unstructured
  ❌ ACP Compliance: 0%
```

### After Agent Processing
```
Product: ELEC-HEADPHONE-015
Completeness Score: 85/100
Improvements:
  ✅ Category: Retail Standard V2 taxonomy
  ✅ Name: Professional format
  ✅ Description: High-quality ACP content (280 words)
  ✅ Images: 2 high-res images + 1 video (CDN-hosted)
  ✅ Attributes: Structured and normalized
  ✅ ACP Compliance: 95%
  
Recommendations:
  ⚠️ Add 2 more product images
  ⚠️ Expand description to 350-500 characters
```

---

## Running the Demo

### Prerequisites
```bash
# Start CRUD service
cd apps/crud-service/src && uvicorn crud_service.main:app --reload --port 8000

# Start product management agents
cd apps/product-management-normalization-classification/src && uvicorn main:app --reload --port 8006 &
cd apps/product-management-acp-transformation/src && uvicorn main:app --reload --port 8007 &
cd apps/product-management-consistency-validation/src && uvicorn main:app --reload --port 8008 &
cd apps/product-management-assortment-optimization/src && uvicorn main:app --reload --port 8009 &
cd apps/ecommerce-product-detail-enrichment/src && uvicorn main:app --reload --port 8002 &
```

### Run Automated Demo
```bash
# Using bash script
bash docs/demos/interactive-scenarios/run-product-lifecycle.sh

# Using PowerShell
.\docs\demos\interactive-scenarios\run-product-lifecycle.ps1
```

---

## Next Steps

1. Explore [Customer Journey Demo](customer-journey.md)
2. Learn about [Order Fulfillment Demo](order-fulfillment.md)
3. Try [CRM Campaign Demo](crm-campaigns.md)
