# Sequence Diagrams

This directory contains detailed sequence diagrams for key flows in the Holiday Peak Hub accelerator.

## Available Diagrams

### 1. [E-commerce Catalog Search](sequence-catalog-search.md)
**Domain**: E-commerce  
**Flow**: Product discovery with SLM-first routing, vector search, and inventory validation

**Key Features**:
- Complexity assessment and model routing
- Azure AI Search integration (vector + hybrid)
- Parallel inventory checks
- Personalization and ranking
- Performance: < 1.2s (P95)

---

### 2. [Inventory Health Check](sequence-inventory-health.md)
**Domain**: Inventory  
**Flow**: Scheduled validation of inventory consistency and anomaly detection

**Key Features**:
- Parallel rule evaluation (negative stock, missing warehouses, etc.)
- Statistical anomaly detection (Z-score)
- Severity classification
- Auto-remediation with SAGA choreography
- Performance: < 6s for 10K SKUs

---

### 3. [Logistics Returns Support](sequence-returns-support.md)
**Domain**: Logistics  
**Flow**: End-to-end returns processing with LLM guidance and SAGA orchestration

**Key Features**:
- Return eligibility validation
- LLM-generated personalized instructions
- Return label generation
- Event-driven SAGA workflow
- VIP fast-track path
- Performance: < 5s (P95)

---

## Diagram Notation

All diagrams use **Mermaid** syntax and follow these conventions:

### Participants
- **Actor**: External user or system (e.g., Customer, Scheduler)
- **API**: FastAPI application endpoint
- **Agent**: Retail agent (orchestrator)
- **Adapter**: Integration adapter (inventory, logistics, CRM, etc.)
- **Memory**: Memory stack (Hot/Warm/Cold)
- **External Systems**: Azure services, carrier APIs, etc.

### Arrows
- **Solid arrows**: Synchronous calls
- **Dotted arrows**: Asynchronous events/responses
- **Parallel blocks**: Concurrent operations

### Notes
- **Step annotations**: Major phases in the flow
- **Decision points**: `alt`/`else` blocks for branching logic
- **Error handling**: Alternative paths for failures

---

## How to Use

### Viewing Diagrams
1. **VS Code**: Install [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid) extension
2. **GitHub**: Mermaid renders natively in GitHub markdown
3. **Online**: Copy to [Mermaid Live Editor](https://mermaid.live/)

### Updating Diagrams
When modifying flows:
1. Update the relevant sequence diagram
2. Update corresponding component documentation
3. Update related ADRs if architectural decisions change
4. Keep performance targets and metrics accurate

---

## Related Documentation
- [Architecture Overview](../architecture.md)
- [ADRs Index](../ADRs.md)
- [Components Documentation](../components/)
- [Operational Playbooks](../playbooks/)

---

## Diagram Standards

### Performance Targets
Always include a performance characteristics table:
| Step | Target Latency | Optimization |
|------|----------------|--------------|
| ... | ... | ... |

### Observability
Document metrics tracked:
```python
metrics.histogram("operation.latency_ms", duration)
metrics.counter("operation.status", {"status": "success|failure"})
```

### Error Handling
Show alternative paths for:
- Service unavailable
- Timeout
- Validation failure
- Policy violation

### Code Examples
Include implementation snippets for:
- Key algorithms
- Policy rules
- Event handlers
- Remediation actions
