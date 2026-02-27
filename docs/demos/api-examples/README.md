# API Examples

**Status**: Phase 1 - Complete

---

## Overview

This directory contains quick-start API examples for all 21 agent services, including curl scripts, PowerShell examples, and Postman collections.

---

## Available Examples

### Quick Start Scripts

#### Bash/curl (Linux/macOS/WSL)
```bash
# Run all quick demos
bash curl-examples.sh all

# Run specific domain demos
bash curl-examples.sh ecommerce
bash curl-examples.sh product-management
bash curl-examples.sh crm
bash curl-examples.sh inventory
bash curl-examples.sh logistics

# Run specific agent demo
bash curl-examples.sh enrichment
bash curl-examples.sh catalog-search
```

#### PowerShell (Windows)
```powershell
# Run all quick demos
.\powershell-examples.ps1 -Domain All

# Run specific domain demos
.\powershell-examples.ps1 -Domain Ecommerce
.\powershell-examples.ps1 -Domain ProductManagement
.\powershell-examples.ps1 -Domain CRM
.\powershell-examples.ps1 -Domain Inventory
.\powershell-examples.ps1 -Domain Logistics

# Run specific agent demo
.\powershell-examples.ps1 -Agent enrichment
```

### Postman Collection

**Import**: `postman-collection.json`

**Environment Variables Required**:
- `CRUD_URL`: http://localhost:8000
- `AGENT_BASE_URL`: http://localhost:8001 (adjust per agent)

**Features**:
- Pre-request scripts for authentication
- Test assertions for response validation
- Sample data variables
- Collection runner support

---

## Quick Reference

### E-Commerce Agents

```bash
# Catalog Search
curl -X POST http://localhost:8001/invoke \
  -H "Content-Type: application/json" \
  -d '{"query": "wireless headphones"}'

# Product Detail Enrichment
curl -X POST http://localhost:8002/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345"}'

# Cart Intelligence
curl -X POST http://localhost:8003/invoke \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123", "action": "get_recommendations"}'

# Checkout Support
curl -X POST http://localhost:8004/invoke \
  -H "Content-Type: application/json" \
  -d '{"cart_id": "cart-123"}'

# Order Status
curl -X POST http://localhost:8005/invoke \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORD-123"}'
```

### Product Management Agents

```bash
# Normalization/Classification
curl -X POST http://localhost:8006/invoke \
  -H "Content-Type: application/json" \
  -d '{"product_data": {"name": "headphones", "category": "audio"}}'

# ACP Transformation
curl -X POST http://localhost:8007/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345"}'

# Consistency Validation
curl -X POST http://localhost:8008/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345"}'

# Assortment Optimization
curl -X POST http://localhost:8009/invoke \
  -H "Content-Type: application/json" \
  -d '{"category": "electronics"}'
```

### CRM Agents

```bash
# Profile Aggregation
curl -X POST http://localhost:8010/invoke \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123"}'

# Segmentation/Personalization
curl -X POST http://localhost:8011/invoke \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123"}'

# Campaign Intelligence
curl -X POST http://localhost:8012/invoke \
  -H "Content-Type: application/json" \
  -d '{"campaign_goal": "increase_aov"}'

# Support Assistance
curl -X POST http://localhost:8013/invoke \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "TKT-123"}'
```

### Inventory Agents

```bash
# Health Check
curl -X POST http://localhost:8014/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345"}'

# JIT Replenishment
curl -X POST http://localhost:8015/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345"}'

# Reservation Validation
curl -X POST http://localhost:8016/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345", "quantity": 2}'

# Alerts/Triggers
curl -X POST http://localhost:8017/invoke \
  -H "Content-Type: application/json" \
  -d '{"alert_type": "low_stock"}'
```

### Logistics Agents

```bash
# ETA Computation
curl -X POST http://localhost:8018/invoke \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORD-123"}'

# Carrier Selection
curl -X POST http://localhost:8019/invoke \
  -H "Content-Type: application/json" \
  -d '{"destination": "90210", "weight": 5}'

# Returns Support
curl -X POST http://localhost:8020/invoke \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORD-123", "reason": "defective"}'

# Route Issue Detection
curl -X POST http://localhost:8021/invoke \
  -H "Content-Type: application/json" \
  -d '{"shipment_id": "SHIP-123"}'
```

---

## Files

- `curl-examples.sh` - Bash script with all agent examples
- `powershell-examples.ps1` - PowerShell script with all agent examples
- `postman-collection.json` - Postman collection with all endpoints
- `sample-requests/` - JSON files with sample request payloads
- `sample-responses/` - JSON files with expected response formats

---

## Next Steps

1. Try [Interactive Scenarios](../interactive-scenarios/)
2. Explore [Jupyter Notebooks](../agent-playgrounds/)
3. Review [Sample Data](../sample-data/)
