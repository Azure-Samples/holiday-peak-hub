# Open Issues Execution Wave Plan

**Last Updated**: March 12, 2026  
**Scope**: All currently open GitHub issues  
**Repository**: Azure-Samples/holiday-peak-hub

---

## Purpose

This plan converts the open-issue backlog into a dependency-ordered implementation sequence, so the team can:

1. Unblock UI-only scenario demonstrations first.
2. Stabilize CRUD contracts and quality gates.
3. Scale connector implementation through reusable architecture patterns.

This strategy is aligned with:
- TOGAF capability progression (foundation before expansion)
- microservices.io patterns (BFF, Saga, Strangler Fig, Database per Service)
- Enterprise Integration Patterns (Message Translator, Idempotent Receiver, Dead-Letter Channel)

---

## Evaluation Model

Each issue is evaluated with the same dimensions:

- **Scenario/UI parity impact**: Critical / High / Medium / Low
- **Architectural risk**: Critical / High / Medium / Low
- **Dependency chain**: blockers and prerequisites
- **Implementation pattern**: explicit architecture pattern
- **Acceptance slices**: thin-path to hardened rollout

---

## Delivery Waves

## Wave 1 — Demo Foundation (Phase 1)

**Goal**: Enable deterministic, UI-only demo execution without Entra dependency blockers.  
**Exit Criteria**:
- Protected UI routes can run in dev with safe mock auth.
- Checkout and payment continuity use real CRUD flow.
- Contract and schema quality gates are in place for active feature work.

**Issues**:
- #214 — UI/Auth mock login mode (dev-only)
- #210 — Checkout stub replacement
- #220 — Payment retrieval + ticket mutation workflows
- #29 — Schema drift test failures

**Recommended Owner Profile**:
- UI platform engineer + CRUD backend engineer + QA owner

---

## Wave 2 — Core Scenario Completeness (Phase 1)

**Goal**: Complete minimum business capability backbone for scenarios 01, 03, and 04.  
**Exit Criteria**:
- Inventory and reservation state is authoritative in CRUD.
- Returns/refunds are lifecycle-driven and auditable.
- Brand-shopping API contracts are stable and test-covered.

**Issues**:
- #215 — Brand-shopping API contracts
- #216 — Inventory domain + reservation persistence
- #217 — Returns creation + refund lifecycle APIs

**Recommended Owner Profile**:
- CRUD domain lead (orders/inventory/returns) + API contract reviewer

---

## Wave 3 — UI Scenario and Notebook Parity (Phase 2)

**Goal**: Execute all mapped scenarios from UI with guided flows and parity status.  
**Exit Criteria**:
- Demo Hub guides scenario execution end-to-end.
- Scenario 03, 04, and 08 user journeys are available in UI.
- Product-truth and brand-shopping parity are visible without notebooks.

**Issues**:
- #209 — Demo Hub + runbooks
- #211 — Returns initiation and refund timeline UX
- #212 — Inventory optimization UI module
- #213 — Support resolution workspace
- #221 — Truth-stage orchestration endpoints for UI parity

**Recommended Owner Profile**:
- Frontend lead + BFF/API integration lead

---

## Wave 4 — Connector Platform Backbone (Phase 3/4)

**Goal**: Establish scalable connector architecture and near-term connector set.  
**Exit Criteria**:
- Event-driven sync blueprint is operational.
- Commerce/PIM/DAM priority connectors follow one adapter template.
- Observability + idempotency + DLQ behavior are standardized.

**Issues**:
- #80 — Event-driven connector sync architecture
- #38, #40, #53, #54, #55, #56, #57, #58, #59 — Commerce/OMS related adapters
- #47, #48, #50, #51, #52, #74, #75, #76, #77 — Product and operations-adjacent adapters

**Recommended Owner Profile**:
- Integration platform team + architecture governance reviewer

---

## Wave 5 — Long-Tail Ecosystem Connectors (Phase 5)

**Goal**: Expand ecosystem coverage after core demo and connector backbone are stable.  
**Exit Criteria**:
- Remaining connectors are implemented using shared adapter scaffold.
- Contract tests and replay-safe sync are applied consistently.

**Issues**:
- #45, #49, #60, #61, #62, #63, #64, #65, #66, #67, #68, #69, #70, #71, #72, #73, #78

**Recommended Owner Profile**:
- Integration delivery squad with reusable playbook ownership

---

## Cross-Wave Governance Rules

1. **Contract-first delivery**: No UI integration without versioned API contract tests.
2. **Idempotency-by-default**: All event-driven flows must tolerate retries and duplicates.
3. **Observability gate**: Every wave must ship with success/failure telemetry and auditability.
4. **Security boundary discipline**: Dev auth mocking must be impossible in production.
5. **Thin slice first**: Deliver happy-path runnable flow before broadening feature depth.

---

## Suggested Cadence

- Weekly architecture review on wave exit criteria.
- Mid-wave contract check (schema/API drift and compatibility).
- End-wave demo review using only the UI against the active dev environment.

---

## Immediate Next 2-Week Focus

1. Close #214, #220, #210, #29 (Wave 1 complete).
2. Start #215 and #216 in parallel after #29 stabilizes shared contracts.
3. Begin #209 shell and route map once #214 is merged.
