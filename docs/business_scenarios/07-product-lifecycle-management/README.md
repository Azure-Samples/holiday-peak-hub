# Business Scenario 07: Product Lifecycle Management

## Overview

**Product Lifecycle Management** covers the end-to-end journey of a product from catalog ingestion through normalization, ACP (Attribute, Category, Property) transformation, consistency validation, and assortment optimization. Holiday Peak Hub uses a sequential pipeline of product management agents that transform raw supplier data into standardized, validated, and optimally assorted products — ensuring catalog quality at scale.

## Business Importance for Retail

| Metric | Impact |
|--------|--------|
| **Catalog Accuracy** | Every 1% improvement in product data quality increases conversion by 2–5% |
| **Time to Market** | AI-driven normalization reduces product onboarding from days to minutes |
| **Search Relevance** | Standardized attributes improve search hit rates by 30–50% |
| **Return Reduction** | Accurate product descriptions reduce "not as described" returns by 20% |
| **Assortment Revenue** | Optimal assortment planning increases revenue per category by 10–15% |
| **Peak Readiness** | Automated validation ensures catalog is clean before high-traffic events |

During peak seasons, retailers must onboard seasonal products quickly, ensure descriptions are accurate across channels, and optimize assortment to maximize revenue within shelf/page constraints. Manual catalog management at scale breaks under holiday volume.

## Traditional Challenges

1. **Inconsistent Data**: Suppliers provide product data in different formats, languages, and quality levels
2. **Manual Normalization**: Product managers manually standardize names, categories, and attributes
3. **No Validation**: Data quality issues (missing attributes, conflicting info) discovered only after customer complaints
4. **Static Assortment**: Category assortment decisions based on gut instinct rather than data
5. **Slow Onboarding**: New products take days to appear in catalog due to manual enrichment
6. **Cross-Channel Gaps**: Product data inconsistencies between web, mobile, and marketplace channels

## How Holiday Peak Hub Addresses It

### Sequential Processing Pipeline

```
product.created → normalization-classification → normalized
normalized → acp-transformation → ACP-transformed
ACP-transformed → consistency-validation → validated / validation_failed
order.placed → assortment-optimization → assortment updated
```

### Four-Stage Quality Gate

Each stage acts as a quality gate — products only progress when the previous stage succeeds. Failed validation triggers a feedback loop back to normalization or manual review.

## Process Flow

### Stage 1: Normalization & Classification

1. **Product created in catalog** → `product.created` event published
2. **Normalization & Classification Agent** (`product-management-normalization-classification`) receives event:
   - Cleans and standardizes product title (casing, abbreviations, brand placement)
   - Normalizes attributes (dimensions to metric, colors to standard palette)
   - Classifies product into taxonomy categories using AI
   - SLM handles standard products; LLM for complex multi-category items
   - Stores normalized data in Cosmos DB
   - Publishes `product.normalized` event

### Stage 2: ACP Transformation

3. **ACP Transformation Agent** (`product-management-acp-transformation`) receives `product.normalized`:
   - Transforms normalized data into ACP (Attribute-Category-Property) structure
   - Maps attributes to category-specific property schemas
   - Fills missing properties using AI inference from description and image metadata
   - Generates faceted search attributes (filterable properties)
   - Publishes `product.acp_transformed` event

### Stage 3: Consistency Validation

4. **Consistency Validation Agent** (`product-management-consistency-validation`) receives `product.acp_transformed`:
   - Validates required attributes per category (e.g., "size" for apparel, "wattage" for electronics)
   - Cross-checks attribute consistency (price vs. category typical range, weight vs. dimensions)
   - Checks image compliance (resolution, background, file size)
   - AI evaluates semantic consistency (title matches description matches attributes)
   - **If valid** → Publishes `product.validated` → product goes live
   - **If violations found** → Publishes `product.validation_failed` with specific violations:
     - Auto-fixable → routes back to normalization agent
     - Requires review → flags for human product manager

### Stage 4: Assortment Optimization

5. **Assortment Optimization Agent** (`product-management-assortment-optimization`) runs on purchase events:
   - Receives `order.placed` events to track product performance
   - Analyzes per-category metrics: sell-through rate, margin, return rate, search demand
   - AI recommends assortment changes:
     - Promote: high-demand, high-margin products → boost in search/category pages
     - Demote: low-performing products → reduce visibility
     - Suggest: gap analysis — categories with high search demand but thin assortment
   - Outputs assortment recommendations to product management team

## Agents Involved

| Agent | Role | Trigger | Output |
|-------|------|---------|--------|
| `product-management-normalization-classification` | Clean, standardize, classify | `product.created` | `product.normalized` |
| `product-management-acp-transformation` | Map to ACP schema, generate facets | `product.normalized` | `product.acp_transformed` |
| `product-management-consistency-validation` | Validate quality, check consistency | `product.acp_transformed` | `product.validated` or `product.validation_failed` |
| `product-management-assortment-optimization` | Analyze performance, optimize mix | `order.placed` (aggregate) | Assortment recommendations |

## Event Hub Topology

```
product-events (product.created)           ──→  normalization-classification
product-events (product.normalized)        ──→  acp-transformation
product-events (product.acp_transformed)   ──→  consistency-validation
product-events (product.validated)         ──→  CRUD Service (publish to catalog)
product-events (product.validation_failed) ──→  normalization-classification (auto-fix) / human review
order-events (order.placed)                ──→  assortment-optimization
```

## Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| Normalization accuracy | > 95% | AI-classified vs. human-verified category |
| ACP completeness | > 90% | Required properties filled per category |
| Validation pass rate | > 85% | Products passing validation on first attempt |
| Auto-fix success rate | > 70% | Validation failures auto-corrected without human intervention |
| Time to catalog | < 5 minutes | Product created → searchable in catalog |
| Assortment revenue lift | > 10% | Revenue change in optimized categories |

## BPMN Diagram

See [product-lifecycle-management.drawio](product-lifecycle-management.drawio) for the complete BPMN 2.0 process diagram showing:
- **5 pools**: Product Events, Normalization Agent, ACP Agent, Validation Agent, Assortment Agent
- **Sequential pipeline**: Create → Normalize → ACP → Validate → Publish
- **Feedback loop**: Validation failed → auto-fix → re-process
- **Parallel stream**: Order events → assortment optimization (independent)
