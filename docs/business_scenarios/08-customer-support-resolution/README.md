# Business Scenario 08: Customer Support Resolution

## Executive Statement

AI-first support resolution loop that compresses response time, improves first-contact resolution, and escalates only high-complexity cases.

## Capability Mapping

| Capability | Business Leverage |
| --- | --- |
| Support assistance agent | Fast triage and intent-aware response drafts |
| Order and returns context retrieval | Higher-quality resolution accuracy |
| Escalation intelligence | Better human handoff for sensitive/complex tickets |
| Knowledge feedback loop | Continuous deflection and service quality improvement |

## Outcome Targets

| North-Star KPI | Target |
| --- | --- |
| First-contact resolution | 60–80% |
| Initial response latency | < 30s |
| Cost per resolved ticket | -50% vs baseline |
| CSAT trend | > 4.2/5 |

## Current API Readiness (Issue #220)

- Staff resolution loop now has CRUD lifecycle coverage with role enforcement:
   - `POST /api/staff/tickets`
   - `PATCH /api/staff/tickets/{id}`
   - `POST /api/staff/tickets/{id}/escalate`
   - `POST /api/staff/tickets/{id}/resolve`
- Ticket mutation responses now include auditable lifecycle metadata (`status_history`, `audit_log`, actor, timestamp, reason).
- Payment context retrieval is now available through `GET /api/payments/{payment_id}` for support workflows (ownership + staff/admin access checks).
- Remaining scenario gap: customer/self-service ticket creation route is still not implemented in CRUD (`/api/tickets` equivalent remains pending).

## Demo Access Enablement (Issue #214)

- Support scenario demos run with role-based access in both auth modes:
   - Entra mode: role claims from sign-in token (`customer`, `staff`, `admin`).
   - Dev fail-safe mode: role-selectable mock login at `/auth/login` (non-production only).
- Staff resolution operations continue to require `staff|admin`; admin-only routes still require `admin`.
- Production safeguard: mock login endpoints return `403` when mock mode is disabled and are never enabled in production runtime.

## Executive Flow

```mermaid
flowchart LR
   A[Support Ticket Created] --> B[Intent + Sentiment Classification]
   B --> C{Complexity Level}
   C -->|Low/Medium| D[AI Resolution Draft]
   D --> E[Context Validation]
   E --> F[Customer Response Sent]
   C -->|High/Risk| G[Human Escalation Package]
   G --> H[Agent Resolution]
   F --> I[Outcome Capture]
   H --> I
   I --> J[Knowledge Base Update]

   classDef a fill:#0B84F3,color:#fff,stroke:#085ea8
   classDef b fill:#00A88F,color:#fff,stroke:#0b6e5f
   classDef c fill:#F39C12,color:#fff,stroke:#af6f0c
   classDef d fill:#8E44AD,color:#fff,stroke:#5b2a70
   class A,B a
   class D,E,F,I,J b
   class C c
   class G,H d
```
