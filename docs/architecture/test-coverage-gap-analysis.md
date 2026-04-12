# Test Coverage Gap Analysis

**Generated**: 2026-04-12  
**Coverage Tool**: pytest-cov v7.13.2  
**Test Suite**: 1796 tests (1136 lib + 660 app)  
**Overall Coverage**: 89.8% (477 tracked files)  
**Target**: 75% minimum per file (governance policy)

---

## Executive Summary

79 of 477 files (16.6%) fall below the 75% coverage floor. The gaps cluster in three dominant patterns:

| Category | Files Below 75% | Avg Coverage | Root Cause |
|----------|-----------------|--------------|------------|
| **Event Handlers** | 19 | 40.3% | Async consumer paths not exercised in unit tests |
| **Agent `agents.py`** | 19 | 51.6% | Foundry invocation branches mocked but not fully covered |
| **Adapters** | 19 | 59.8% | External API call paths and error branches |
| **Other** | 22 | 54.2% | CRUD repositories, conftest fixtures, schemas |

---

## Priority 1: Event Handlers (19 files, avg 40.3%)

Event handlers process Azure Event Hub messages asynchronously. The low coverage is structural — these paths involve deserialization, domain-specific processing, and error handling that unit tests mock at the boundary.

| File | Coverage | Missing Path |
|------|----------|--------------|
| `product-management-assortment-optimization/event_handlers.py` | 24% | Optimization loop, batch processing |
| `inventory-health-check/event_handlers.py` | 27% | Anomaly detection flow, remediation branch |
| `truth-enrichment/event_handlers.py` | 28% | Guardrail rejection path, partial enrichment |
| `logistics-carrier-selection/event_handlers.py` | 37% | Rate comparison, multi-carrier fallback |
| `logistics-eta-computation/event_handlers.py` | 37% | Delay computation, carrier API errors |
| `logistics-returns-support/event_handlers.py` | 37% | Label generation, eligibility check |
| `logistics-route-issue-detection/event_handlers.py` | 37% | Rerouting decision tree |
| `crm-campaign-intelligence/event_handlers.py` | 38% | ROI prediction, channel selection |
| `truth-export/event_handlers.py` | 41% | PIM writeback, schema transformation |
| `crm-support-assistance/event_handlers.py` | 44% | Ticket classification, escalation path |
| `ecommerce-product-detail-enrichment/event_handlers.py` | 44% | SEO enrichment, image processing |
| `crm-segmentation-personalization/event_handlers.py` | 46% | Cohort creation, behavioral clustering |
| `inventory-alerts-triggers/event_handlers.py` | 46% | Threshold alerting, notification dispatch |
| `inventory-jit-replenishment/event_handlers.py` | 46% | Demand forecast, auto-reorder |
| `product-management-acp-transformation/event_handlers.py` | 46% | ACP mapping, attribute extraction |
| `product-management-normalization-classification/event_handlers.py` | 46% | Taxonomy mapping, normalization |
| `crm-profile-aggregation/event_handlers.py` | 46% | Profile merge, deduplication |
| `ecommerce-order-status/event_handlers.py` | 48% | Tracking enrichment, notification |
| `ecommerce-cart-intelligence/event_handlers.py` | 48% | Cross-sell, abandonment detection |

**Recommended Test Strategy:**
1. Add `pytest-asyncio` integration tests that simulate Event Hub `EventData` payloads
2. Test the full `process_event()` → adapter → memory → response path per handler
3. Cover error branches: malformed events, adapter timeouts, duplicate events
4. Use `conftest.py` Event Hub mocking fixtures from `apps/conftest.py`

---

## Priority 2: Agent Modules (19 files, avg 51.6%)

Agent `agents.py` files contain the core intelligence logic — tool definitions, MCP registrations, and invocation handlers. Coverage gaps are in model invocation branches that require Foundry mock fixtures.

| File | Coverage | Missing Path |
|------|----------|--------------|
| `product-management-assortment-optimization/agents.py` | 43% | Optimization scoring, batch analysis |
| `product-management-consistency-validation/agents.py` | 44% | Cross-channel validation, quality scoring |
| `truth-enrichment/agents.py` | 46% | Guardrail enforcement, confidence scoring |
| `crm-profile-aggregation/agents.py` | 46% | 360° view assembly, data reconciliation |
| `product-management-normalization-classification/agents.py` | 48% | Taxonomy resolution, attribute mapping |
| `inventory-jit-replenishment/agents.py` | 49% | Demand prediction, reorder logic |
| `product-management-acp-transformation/agents.py` | 49% | Canonical format mapping |
| `crm-segmentation-personalization/agents.py` | 49% | Segment creation, behavioral analysis |
| `crm-support-assistance/agents.py` | 50% | Ticket routing, resolution suggestion |
| `inventory-reservation-validation/agents.py` | 50% | Conflict detection, hold management |
| `logistics-route-issue-detection/agents.py` | 51% | Delay classification, rerouting |
| `logistics-carrier-selection/agents.py` | 52% | Rate optimization, SLA matching |
| `logistics-eta-computation/agents.py` | 52% | Multi-carrier ETA, delay modeling |
| `logistics-returns-support/agents.py` | 52% | Eligibility rules, label workflow |
| `inventory-alerts-triggers/agents.py` | 55% | Alert threshold logic, suppression |
| `truth-hitl/agents.py` | 55% | Review decision tree, audit logging |
| `inventory-health-check/agents.py` | 57% | Accuracy scoring, cycle scheduling |
| `crm-campaign-intelligence/agents.py` | 69% | Channel ROI computation |
| `truth-export/agents.py` | 72% | Format transformation, writeback |

**Recommended Test Strategy:**
1. Create a shared `foundry_mock` fixture that returns configurable `AgentResponse` objects
2. Test each MCP tool function independently with direct invocation
3. Test the `invoke()` method with SLM and LLM branch paths
4. Cover tool-calling chains (agent A calls agent B's MCP tool)

---

## Priority 3: Adapters (19 files, avg 59.8%)

Adapters handle external API calls and data transformation. Coverage gaps are in error paths and external API response handling.

| File | Coverage | Gap Area |
|------|----------|----------|
| `lib/.../crud_adapter.py` | 38% | HTTP error paths, retry logic |
| `crm-segmentation-personalization/adapters.py` | 42% | Segment API errors |
| `lib/.../crm_adapter.py` | 46% | Profile merge conflicts |
| `lib/.../mock_adapters.py` | 56% | Unused mock variants |
| `lib/.../pricing_adapter.py` | 56% | Dynamic pricing paths |
| `product-management-normalization-classification/adapters.py` | 57% | Taxonomy API |
| `product-management-consistency-validation/adapters.py` | 60% | Validation rule engine |
| `truth-enrichment/adapters.py` | 60% | Enrichment pipeline stages |
| `crm-campaign-intelligence/adapters.py` | 61% | Channel optimization |
| `crm-support-assistance/adapters.py` | 61% | Ticket system integration |
| `product-management-assortment-optimization/adapters.py` | 61% | Assortment scoring |
| `lib/.../inventory_adapter.py` | 61% | Stock check variants |
| `inventory-alerts-triggers/adapters.py` | 62% | Notification dispatch |
| `inventory-health-check/adapters.py` | 64% | Health scoring |
| `inventory-reservation-validation/adapters.py` | 68% | Hold conflict resolution |
| `logistics-eta-computation/adapters.py` | 69% | Carrier API integration |
| `logistics-returns-support/adapters.py` | 69% | Return label generation |
| `logistics-carrier-selection/adapters.py` | 72% | Rate comparison |
| `lib/.../product_adapter.py` | 72% | Product CRUD calls |

**Recommended Test Strategy:**
1. Add `httpx.MockTransport` or `respx` fixtures for HTTP adapter tests
2. Test each adapter method with success, error (4xx, 5xx), and timeout scenarios
3. Cover retry/circuit-breaker behavior with controlled failure injection
4. Stub CRUD endpoints using FastAPI test client

---

## Priority 4: Lib Core Gaps

| File | Coverage | Issue |
|------|----------|-------|
| `lib/.../agents/memory/builder.py` | 31% | `gather_adapters()` parallel I/O paths |
| `lib/tests/test_agents_builder.py` | 42% | Test file itself has dead branches |
| `lib/.../utils/event_hub.py` | 50% | Consumer lifecycle, checkpoint logic |
| `lib/.../agents/orchestration/evaluator.py` | 52% | Complexity evaluation branches |

**Recommended Test Strategy:**
1. `memory/builder.py`: Add tests for parallel `asyncio.gather` with Redis failure, Cosmos timeout, and partial success scenarios
2. `event_hub.py`: Test consumer group lifecycle, offset management, and error recovery
3. `evaluator.py`: Test all complexity classification thresholds

---

## Coverage by Domain (Heat Map)

| Domain | Files | Avg Coverage | Critical Gaps |
|--------|-------|-------------|---------------|
| **eCommerce** | 25 | 83% | event_handlers (44-48%), adapters (60-72%) |
| **CRM** | 20 | 78% | agents (46-69%), event_handlers (38-46%) |
| **Inventory** | 20 | 76% | event_handlers (27-46%), agents (49-57%) |
| **Logistics** | 20 | 77% | event_handlers (37%), agents (51-52%) |
| **Product Mgmt** | 20 | 72% | event_handlers (24-46%), agents (43-49%) |
| **Search** | 8 | 85% | ai_search.py (60%) |
| **Truth Layer** | 16 | 74% | schemas_compat (17%), event_handlers (28-41%) |
| **CRUD Service** | 25 | 82% | repositories (30-60%), consumers (45%) |
| **Lib Core** | 53+ | 91% | memory/builder (31%), crud_adapter (38%) |

---

## Remediation Plan

### Wave 1 — Lib Core (Week 1)
- [ ] `memory/builder.py` → Add parallel I/O failure tests (target: 80%)
- [ ] `crud_adapter.py` → Add HTTP error path tests (target: 80%)
- [ ] `event_hub.py` → Add consumer lifecycle tests (target: 75%)
- [ ] `evaluator.py` → Add complexity threshold tests (target: 75%)

### Wave 2 — Event Handlers (Weeks 2-3)
- [ ] Create shared Event Hub test fixtures in `apps/conftest.py`
- [ ] Add integration tests for all 19 event handler files (target: 70%)
- [ ] Cover: deserialization, happy path, error path, duplicate detection

### Wave 3 — Agents (Weeks 3-4)
- [ ] Create shared Foundry mock fixture
- [ ] Add MCP tool unit tests for all 19 agent files (target: 70%)
- [ ] Cover: SLM path, LLM escalation, tool chains

### Wave 4 — Adapters (Week 4)
- [ ] Add HTTP mock tests for all 19 adapter files (target: 75%)
- [ ] Cover: success, 4xx, 5xx, timeout, retry

**Expected outcome**: Overall coverage from 89.8% → 93%+, with 0 files below 60%.

---

## Related

- [Governance Policy: 75% coverage floor](../governance/backend-governance.md)
- [Lib README: Testing section](../../lib/README.md)
- [CI/CD: Test workflow](../../.github/workflows/)
