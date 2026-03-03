# ADR-025: Product Truth Layer Architecture

**Status**: Accepted  
**Date**: 2026-03  
**Deciders**: Architecture Team

## Context

AI-enriched product data (descriptions, SEO content, attributes) requires validation before publication. LLMs can generate:
- Factually incorrect specifications
- Brand guideline violations  
- Inappropriate or biased language
- Regulatory compliance issues (e.g., misleading health claims)

Additionally, retailers need to:
- Audit AI changes before they reach customers
- Maintain a "golden record" of approved product data
- Sync approved changes back to PIM systems
- Track who approved what and when

Key questions addressed:
- How do we store AI-enriched data separately from source data?
- How do we implement human-in-the-loop (HITL) review workflows?
- How do we sync approved changes to PIM systems?
- How do we ensure auditability and rollback capability?

## Decision

**Implement a Product Truth Layer with three components: Truth Store, HITL Workflow, and PIM Writeback.**

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Product Truth Layer                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────┐    ┌─────────────────┐    ┌──────────────────┐         │
│  │ Source PIM  │───▶│  Truth Store    │───▶│  PIM Writeback   │         │
│  │ (Akeneo,    │    │  (Cosmos DB)    │    │  (Sync Service)  │         │
│  │  Salsify)   │    │                 │    │                  │         │
│  └─────────────┘    │  ┌───────────┐  │    └────────┬─────────┘         │
│                     │  │ Raw Data  │  │             │                    │
│  ┌─────────────┐    │  ├───────────┤  │    ┌───────▼────────┐           │
│  │ AI Enrichment│──▶│  │ Enriched  │  │    │  Target PIM    │           │
│  │ (Agents)    │    │  ├───────────┤  │    │  (Golden       │           │
│  └─────────────┘    │  │ Approved  │◀─┼────│   Record)      │           │
│                     │  └───────────┘  │    └────────────────┘           │
│  ┌─────────────┐    │                 │                                  │
│  │ Staff UI    │───▶│   HITL Queue    │                                  │
│  │ (Review)    │    │                 │                                  │
│  └─────────────┘    └─────────────────┘                                  │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component 1: Truth Store

A versioned product data store in Cosmos DB with three data layers:

```python
from holiday_peak_lib.schemas.truth import TruthRecord, TruthStatus

@dataclass
class TruthRecord:
    """Single source of truth for product data."""
    
    # Identity
    sku: str
    tenant_id: str
    
    # Data Layers
    source_data: dict           # Original PIM data
    enriched_data: dict         # AI-generated enhancements
    approved_data: dict | None  # Human-approved final version
    
    # Status
    status: TruthStatus         # PENDING, APPROVED, REJECTED
    
    # Audit
    version: int
    created_at: datetime
    updated_at: datetime
    enriched_by: str            # Agent ID
    approved_by: str | None     # Staff user ID
    approval_notes: str | None
    
    # Lineage
    source_connector: str       # "akeneo", "salsify"
    source_version: str         # PIM version ID
```

**Data Layer Semantics**:
| Layer | Source | Mutability | Visibility |
|-------|--------|------------|------------|
| `source_data` | PIM sync | Immutable (per version) | Internal |
| `enriched_data` | AI agents | Append-only | Staff review |
| `approved_data` | HITL approval | Immutable (per approval) | Customer-facing |

### Component 2: HITL Workflow

Human-in-the-loop review process for AI-enriched content:

```python
from holiday_peak_lib.truth import HITLWorkflow, ReviewDecision

class HITLWorkflow:
    """Manages human review of AI-enriched products."""
    
    async def submit_for_review(self, sku: str, enriched_data: dict) -> str:
        """Queue product for human review."""
        review_id = str(uuid4())
        
        await self.truth_store.update(
            sku=sku,
            enriched_data=enriched_data,
            status=TruthStatus.PENDING_REVIEW,
        )
        
        await self.event_bus.publish(
            topic="truth.review.requested",
            payload={"sku": sku, "review_id": review_id},
        )
        
        return review_id
    
    async def approve(
        self,
        sku: str,
        reviewer_id: str,
        notes: str | None = None,
    ) -> TruthRecord:
        """Approve enriched data for publication."""
        record = await self.truth_store.get(sku)
        
        # Promote enriched → approved
        record.approved_data = record.enriched_data
        record.status = TruthStatus.APPROVED
        record.approved_by = reviewer_id
        record.approval_notes = notes
        record.version += 1
        
        await self.truth_store.save(record)
        
        # Trigger writeback
        await self.event_bus.publish(
            topic="truth.approved",
            payload={"sku": sku, "version": record.version},
        )
        
        return record
    
    async def reject(
        self,
        sku: str,
        reviewer_id: str,
        reason: str,
    ) -> TruthRecord:
        """Reject enriched data with feedback."""
        record = await self.truth_store.get(sku)
        
        record.status = TruthStatus.REJECTED
        record.approved_by = reviewer_id
        record.approval_notes = reason
        
        await self.truth_store.save(record)
        
        # Notify agent for re-enrichment
        await self.event_bus.publish(
            topic="truth.rejected",
            payload={"sku": sku, "reason": reason},
        )
        
        return record
```

**Review States**:
```
PENDING_ENRICHMENT → PENDING_REVIEW → APPROVED → SYNCED
                                   ↳ REJECTED → PENDING_ENRICHMENT (re-enrich)
```

### Component 3: PIM Writeback

Sync approved changes back to source PIM systems:

```python
from holiday_peak_lib.truth import PIMWriteback, WritebackResult

class PIMWriteback:
    """Synchronizes approved data to PIM systems."""
    
    def __init__(self, connector: PIMConnector):
        self.connector = connector
        self.circuit_breaker = CircuitBreaker(name="pim-writeback")
    
    async def sync(self, record: TruthRecord) -> WritebackResult:
        """Push approved data to PIM."""
        if record.status != TruthStatus.APPROVED:
            raise InvalidStateError(f"Cannot sync non-approved record: {record.sku}")
        
        try:
            # Transform to PIM schema
            pim_payload = self._transform_to_pim(record.approved_data)
            
            # Write to PIM with resilience
            result = await self.connector.update_product(
                sku=record.sku,
                data=pim_payload,
            )
            
            # Update truth record status
            record.status = TruthStatus.SYNCED
            record.synced_at = datetime.utcnow()
            record.sync_result = result
            
            await self.truth_store.save(record)
            
            return WritebackResult(
                success=True,
                sku=record.sku,
                pim_version=result.version,
            )
            
        except ConnectorError as e:
            # Log for retry queue
            await self.retry_queue.enqueue(record.sku, str(e))
            return WritebackResult(
                success=False,
                sku=record.sku,
                error=str(e),
            )
```

**Writeback Strategies**:
| Strategy | Use Case | Configuration |
|----------|----------|---------------|
| Immediate | Low-volume, high-priority | `WRITEBACK_MODE=immediate` |
| Batched | High-volume, cost-sensitive | `WRITEBACK_MODE=batch`, `BATCH_SIZE=100` |
| Scheduled | Non-urgent updates | `WRITEBACK_MODE=scheduled`, `CRON=0 2 * * *` |

### Staff Review UI Integration

The HITL workflow integrates with the Staff Review UI:

```typescript
// apps/ui/app/staff/review/page.tsx

interface ReviewQueueItem {
  sku: string;
  productName: string;
  status: 'pending' | 'approved' | 'rejected';
  enrichedFields: string[];
  submittedAt: Date;
  priority: 'high' | 'medium' | 'low';
}

// Diff view showing source vs enriched
interface ProductDiff {
  field: string;
  source: string;       // Original PIM value
  enriched: string;     // AI-generated value
  confidence: number;   // AI confidence score
}
```

### Event Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│ PIM Sync │───▶│ Enrichment│───▶│  HITL    │───▶│ Writeback│───▶│  PIM    │
│          │    │  Agent   │    │ Review   │    │ Service  │    │         │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └─────────┘
     │               │               │               │               │
     │  truth.       │  truth.       │  truth.       │  truth.       │
     │  imported     │  enriched     │  approved     │  synced       │
     ▼               ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Event Hubs (Event Stream)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Cosmos DB Partition Strategy

```python
# Partition key: /tenant_id/category
# Enables efficient queries by tenant and category

TRUTH_CONTAINER_CONFIG = {
    "partition_key": "/partition_key",
    "indexing_policy": {
        "includedPaths": [
            {"path": "/sku/?"},
            {"path": "/status/?"},
            {"path": "/updated_at/?"},
        ],
        "excludedPaths": [
            {"path": "/source_data/*"},
            {"path": "/enriched_data/*"},
        ],
    },
    "ttl": -1,  # No expiration
}
```

## Consequences

### Positive
- **Auditability**: Complete history of source → enriched → approved
- **Rollback**: Revert to any previous version
- **Quality control**: Human approval prevents AI hallucinations reaching customers
- **PIM agnostic**: Writeback works with any PIM connector
- **Decoupled**: Enrichment, review, and sync are independent

### Negative
- **Latency**: HITL adds delay between enrichment and publication
- **Staffing**: Requires human reviewers for HITL queue
- **Storage**: Three data layers multiply storage requirements
- **Complexity**: Multiple services to maintain

### Risks Mitigated
- **AI hallucinations**: Human review catches factual errors
- **Brand violations**: Reviewers ensure guideline compliance
- **Data loss**: Versioned records enable recovery
- **Audit failures**: Complete lineage for compliance

## Alternatives Considered

### 1. Direct PIM Enrichment (No Truth Layer)
**Rejected**: No audit trail; AI errors go directly to production; no rollback capability.

### 2. Git-Based Version Control
**Considered**: Good for devs, but overkill for product data; Cosmos DB change feed provides versioning.

### 3. Approval via PIM Workflow
**Rejected**: PIM workflows vary by vendor; centralized HITL provides consistent UX.

### 4. Automated Approval with Confidence Threshold
**Deferred**: Possible future enhancement where high-confidence enrichments auto-approve.

## Implementation Notes

- See `lib/src/holiday_peak_lib/truth/` for Truth Store implementation
- See `apps/truth-hitl-service/` for HITL workflow service
- See `apps/truth-export-service/` for PIM writeback service
- See `apps/ui/app/staff/` for Staff Review UI pages
- Event topics: `truth.imported`, `truth.enriched`, `truth.approved`, `truth.rejected`, `truth.synced`

## References

- [Human-in-the-Loop ML](https://docs.microsoft.com/en-us/azure/machine-learning/concept-human-in-the-loop)
- [Event Sourcing Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- ADR-008: Memory Tiers (Cosmos DB for warm storage)
- ADR-017: AG-UI Protocol (staff UI integration)
- ADR-024: Connector Registry (PIM connector resolution)
