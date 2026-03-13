# Issue #217 — Strict Implementation Architecture (Returns + Refund Lifecycle)

**Date**: March 12, 2026  
**Status**: Ready for Implementation  
**Scope Lock**: customer return creation endpoint, return lifecycle transitions, refund progression APIs + event publication, shared lifecycle states (staff + customer), SLA timestamps.

---

## 1) Exact File-Level Plan (CRUD + UI)

## CRUD Service (`apps/crud-service`)

### A. Modify existing files

1. `src/crud_service/routes/staff/returns.py`
   - Replace current `approve`-only behavior with full lifecycle transition endpoints for staff operations.
   - Keep `GET /api/staff/returns` as shared read model source.

2. `src/crud_service/main.py`
   - Keep current staff router include.
   - Add include for new customer returns router (proposed prefix: `/api/returns`).

3. `src/crud_service/integrations/event_publisher.py`
   - Add topic support for returns lifecycle events.
   - Add convenience methods for return/refund event publication.

4. `tests/unit/test_staff_returns.py` (existing)
   - Extend for new transition guards and SLA timestamps in staff transitions.

5. `tests/integration/test_returns_api.py`
   - Validate full customer+staff lifecycle path and shared read model behavior.

### B. Add new files

1. `src/crud_service/routes/returns.py`
   - Customer-facing endpoints:
     - create return request
     - list own returns
     - get own return by id
     - refund progression endpoints (customer-safe reads, no privileged transitions)

2. `src/crud_service/repositories/return_request.py`
   - Dedicated `ReturnRequestRepository(BaseRepository)` for `return_requests` container.

3. `src/crud_service/repositories/refund.py`
   - Dedicated `RefundRepository(BaseRepository)` for `refunds` container.

4. `tests/unit/test_returns_routes.py`
   - Unit tests for customer creation, ownership checks, invalid transitions, idempotency.

5. `tests/integration/test_returns_api.py`
   - End-to-end API validation: create → staff transitions → refund progression.

## UI (`apps/ui`)

### A. Modify existing files

1. `lib/api/endpoints.ts`
   - Add customer returns endpoints (`/api/returns/...`).
   - Expand staff returns endpoints for all staff lifecycle actions.

2. `lib/types/api.ts`
   - Replace broad `Return.status: string` with strict union state.
   - Add SLA timestamp fields and refund progression model.

3. `lib/services/staffService.ts`
   - Add transition methods for staff (approve/reject/receive/restock/refund).

4. `lib/hooks/useStaff.ts`
   - Add mutation hooks for each staff transition + cache invalidation for shared keys.

5. `app/staff/requests/page.tsx`
   - Reuse existing returns table.
   - Add deterministic action controls that call transition hooks.

6. `tests/unit/pagesRender.test.tsx`
   - Update mocked return shape to include strict state + SLA timestamps.

### B. Add new files

1. `lib/services/returnsService.ts`
   - Customer return create/list/get + refund progression read methods.

2. `lib/hooks/useReturns.ts`
   - Customer hooks for return initiation and timeline retrieval.

3. `app/orders/page.tsx` (no new route required)
   - Integrate a minimal “request return” action per eligible order row.

4. `tests/unit/returnsServices.test.ts`
   - Contract tests for customer and staff endpoint wiring.

---

## 2) State Machine + Transition Constraints

## Canonical shared return states

`requested` → `approved`/`rejected` → `received` → `restocked` → `refunded`

Terminal states:
- `rejected`
- `refunded`

### Allowed transitions (deterministic)

- `requested -> approved`
- `requested -> rejected`
- `approved -> received`
- `received -> restocked`
- `restocked -> refunded`

### Forbidden transitions (examples)

- `requested -> received`
- `approved -> refunded`
- `rejected -> *`
- `refunded -> *`

### Transition contract behavior

- Invalid transition: `409 Conflict`
- Missing entity: `404 Not Found`
- Ownership/role failure: `403 Forbidden`
- Duplicate terminal transition request (same target state): `200 OK` with no-op marker (`idempotent=true`)

### Actor constraints

- Customer role:
  - allowed: create (`requested`), read own return/refund progression
  - not allowed: lifecycle transitions beyond `requested`
- Staff role:
  - allowed: all operational transitions (`approve/reject/receive/restock/refund`)

### SLA timestamps (required in response model)

- `requested_at`
- `approved_at`
- `rejected_at`
- `received_at`
- `restocked_at`
- `refunded_at`
- `last_transition_at`

All timestamps are ISO 8601 UTC strings and nullable except `requested_at`.

---

## 3) Endpoint Contracts + Event Publication Points

## HTTP contracts (v1, additive)

### Customer

- `POST /api/returns`
  - Body: `{ order_id, reason, items? }`
  - Result: return resource with `status=requested`, SLA timestamps initialized.

- `GET /api/returns`
  - List own returns, sorted by `created_at DESC`.

- `GET /api/returns/{return_id}`
  - Get own return timeline and refund progression.

### Staff

- `GET /api/staff/returns`
- `POST /api/staff/returns/{return_id}/approve`
- `POST /api/staff/returns/{return_id}/reject`
- `POST /api/staff/returns/{return_id}/receive`
- `POST /api/staff/returns/{return_id}/restock`
- `POST /api/staff/returns/{return_id}/refund`

Each transition endpoint returns full canonical return resource including:
- `status`
- `status_history[]`
- SLA timestamps
- `refund` sub-object (when applicable)

## Event publication points (CRUD owns publication)

Publish after successful DB write (never before):

1. On customer creation (`requested`):
   - Topic: `return-events`
   - Event: `ReturnRequested`

2. On each staff transition:
   - Topic: `return-events`
   - Events: `ReturnApproved`, `ReturnRejected`, `ReturnReceived`, `ReturnRestocked`

3. On refund transition:
   - Topic: `payment-events`
   - Event: `RefundIssued` (existing payment domain alignment)
   - Topic: `return-events`
   - Event: `ReturnRefunded` (lifecycle closure)

### Event shape (minimum)

```json
{
  "event_type": "ReturnApproved",
  "data": {
    "return_id": "...",
    "order_id": "...",
    "user_id": "...",
    "status": "approved",
    "occurred_at": "2026-03-12T10:00:00Z",
    "actor_id": "staff-123",
    "actor_roles": ["staff"],
    "sla": {
      "requested_at": "...",
      "approved_at": "..."
    }
  },
  "timestamp": "2026-03-12T10:00:00Z"
}
```

---

## 4) Patterns and Rationale

1. **State Machine for lifecycle enforcement** (microservices.io state transition style)
   - Prevents ambiguous updates and guarantees deterministic progression.

2. **Idempotent Receiver** (Enterprise Integration Patterns)
   - Transition endpoints and event handling tolerate retries safely.

3. **Database per Service ownership** (microservices.io)
   - CRUD remains source of truth for return/refund transactional state.

4. **Shared read model for customer/staff**
   - One canonical lifecycle enum eliminates status drift between views.

5. **Architecture Building Block: auditability** (TOGAF)
   - SLA timestamps + status history provide operational traceability.

6. **Simplicity first** (Agile principle + implementation constraint)
   - No extra workflow branches, no asynchronous orchestrator for v1.

---

## 5) Test Strategy

## Unit (CRUD)

- Transition matrix tests:
  - all allowed transitions succeed
  - all forbidden transitions return `409`
- Role/ownership tests:
  - customer can only create/read own
  - staff-only transitions enforced
- Timestamp tests:
  - correct SLA field set exactly once per transition
- Idempotency tests:
  - repeated terminal transition returns deterministic no-op response

## Integration (CRUD)

- API happy path:
  - create → approve → receive → restock → refund
- Rejection path:
  - create → reject (terminal)
- Event emission assertions:
  - one event per successful transition
  - no event on rejected/failed transition

## UI tests

- Endpoint contract tests for services/hooks
- Staff request page action rendering by state
- Customer order page return initiation visibility + mutation call

## Non-goals for this issue

- No external warehouse/refund-provider callback ingestion.
- No new saga/orchestration coordinator process.

---

## 6) Rollout and Compatibility

## Rollout phases

1. **Phase A (non-breaking contracts)**
   - Add new endpoints and models with additive fields only.
   - Keep existing `GET /api/staff/returns` and `PATCH /approve` available.

2. **Phase B (UI adoption)**
   - UI switches to canonical status union and new transition methods.
   - Customer return creation enabled in orders page.

3. **Phase C (deprecation)**
   - Mark legacy `PATCH /api/staff/returns/{id}/approve` deprecated.
   - Retire only after UI + tests fully migrated.

## Compatibility rules

- Existing consumers reading `status` as string remain functional.
- New timestamp fields are additive and nullable.
- No breaking route removals in initial merge.

## Operational guardrails

- Feature flags (optional):
  - `RETURNS_CUSTOMER_CREATE_ENABLED`
  - `RETURNS_REFUND_TRANSITIONS_ENABLED`
- On publication failures: retain successful DB transition and log publish error for retry handling (eventual consistency over rollback).

---

## ADR Draft (proposed)

**Title**: ADR-0XX — Deterministic Returns/Refund Lifecycle in CRUD  
**Decision**: Implement a single canonical return state machine owned by CRUD, with strict transition guards, role-aware endpoints, SLA timestamps, and post-commit event publication.  
**Consequences**:
- Pros: deterministic behavior, clear auditability, UI/staff parity.
- Cons: requires explicit migration of legacy staff-only endpoint usage.
