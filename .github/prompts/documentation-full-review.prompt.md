# Full Documentation Review & Update

## Objective

Perform a **comprehensive, critical, document-by-document review** of ALL documentation in the repository — the `docs/` folder and every `README.md` file across the codebase — and update each to reflect the **current state** of the solution with deep technical insights, visual clarity, and cohesive narrative.

The final documentation set must explain **what Holiday Peak Hub is**, **why it exists**, **how it works**, and **how to operate it** — both visually (Mermaid diagrams, tables, flow charts) and in writing.

---

## Execution Strategy

Work through the documentation corpus in **7 sequential waves**, each delegated to the appropriate specialist agent. After each wave, the orchestrator validates alignment before proceeding.

---

## Wave 1: Business Context & Value Proposition

**Agent**: `BusinessStrategist` via `#runSubagent`

**Scope**: Review and update business-facing documentation.

**Files to review/update**:
- `docs/architecture/business-summary.md`
- `docs/business_scenarios/README.md`
- `docs/business_scenarios/01-order-to-fulfillment/README.md`
- `docs/business_scenarios/02-product-discovery-enrichment/README.md`
- `docs/business_scenarios/03-returns-refund-processing/README.md`
- `docs/business_scenarios/04-inventory-optimization/README.md`
- `docs/business_scenarios/05-shipment-delivery-tracking/README.md`
- `docs/business_scenarios/06-customer-360-personalization/README.md`
- `docs/business_scenarios/07-product-lifecycle-management/README.md`
- `docs/business_scenarios/08-customer-support-resolution/README.md`
- `docs/business_scenarios/competitive-intelligence-enrichment-search.md`
- `docs/business_scenarios/cost-benefit-enrichment-search.md`
- `docs/business_scenarios/risk-assessment-enrichment-search.md`

**Acceptance criteria**:
- [ ] Each business scenario document articulates: the business problem, KPIs impacted, how the agentic approach differs from traditional microservices, and measurable value delivered
- [ ] Stakeholder map updated (who benefits: CTO, VP Commerce, Ops Manager, Developer)
- [ ] Domain boundaries documented as bounded contexts with clear ownership
- [ ] Non-functional requirements (SLAs, compliance, scaling targets) stated for each domain
- [ ] Competitive positioning narrative: why agentic retail vs. traditional approaches
- [ ] All documents dated and versioned consistently

---

## Wave 2: Architecture & ADR Review

**Agent**: `SystemArchitect` via `#runSubagent`

**Scope**: Review and update all architecture documentation and ADRs for accuracy and completeness.

**Files to review/update**:
- `docs/architecture/README.md`
- `docs/architecture/architecture.md`
- `docs/architecture/solution-architecture-overview.md`
- `docs/architecture/solution-architecture-diagrams.md`
- `docs/architecture/components.md`
- `docs/architecture/index.md`
- `docs/architecture/design-enrichment-search-flows.md`
- `docs/architecture/eventhub-topology-matrix.md`
- `docs/architecture/maf-integration-rationale.md`
- `docs/architecture/foundry-agents-vs-direct-api-report.md`
- `docs/architecture/crud-service-implementation.md`
- `docs/architecture/architecture-compliance-review.md`
- `docs/architecture/standalone-deployment-guide.md`
- `docs/architecture/test-coverage-gap-analysis.md`
- `docs/architecture/ADRs.md` (index)
- All 27 ADRs in `docs/architecture/adrs/adr-001-*.md` through `adr-027-*.md`

**Acceptance criteria**:
- [ ] Each ADR follows the standard template: Status, Context, Decision, Consequences, Alternatives Considered
- [ ] ADRs cross-reference related ADRs and link to implementation evidence
- [ ] Architecture overview matches current deployed state (26 agents, CRUD service, UI, Event Hubs, memory tiers, Flux GitOps, AGC edge, APIM)
- [ ] Component responsibility matrix is current and complete
- [ ] Data flow diagrams match actual adapter/event/MCP communication paths
- [ ] Technology stack rationale is documented for every major choice
- [ ] Sequence diagrams validated against actual code paths
- [ ] Pattern catalog (Builder, Adapter, Saga choreography, Tiered Cache) correctly described

---

## Wave 3: Visual Architecture & Diagrams

**Agent**: `UIDesigner` via `#runSubagent`

**Scope**: Review and update all visual architecture artifacts for accuracy, consistency, and readability.

**Files to review/update**:
- `docs/architecture/diagrams/README.md`
- `docs/architecture/diagrams/c4-system-context.drawio`
- `docs/architecture/diagrams/c4-container-azure-runtime.drawio`
- `docs/architecture/diagrams/c4-component-detailed.drawio`
- `docs/architecture/diagrams/c4-component-summary.drawio`
- `docs/architecture/diagrams/holiday-peak-hub-architecture.drawio`
- `docs/architecture/diagrams/sequence-catalog-search.md`
- `docs/architecture/diagrams/sequence-flux-gitops-deployment.md`
- `docs/architecture/diagrams/sequence-foundry-agent-invocation.md`
- `docs/architecture/diagrams/sequence-inventory-health.md`
- `docs/architecture/diagrams/sequence-memory-parallel-io.md`
- `docs/architecture/diagrams/sequence-returns-support.md`
- All inline Mermaid diagrams in `docs/architecture/architecture.md` and `docs/architecture/solution-architecture-overview.md`

**Acceptance criteria**:
- [ ] All Mermaid diagrams use the repository-standard theme (dark base with `primaryColor:#FFB3BA`, `lineColor:#BAE1FF`)
- [ ] C4 diagrams (draw.io) reflect current system: 26 agents in AKS, CRUD service, UI on SWA, APIM gateway, AGC edge, Event Hubs, three-tier memory, AI Search, Flux GitOps
- [ ] Sequence diagrams match actual flow: FoundryAgentInvoker, memory parallel I/O, MCP tool exposition
- [ ] Visual hierarchy: Context → Container → Component → Code levels clearly separated
- [ ] Consistent icon set across all diagrams (Azure icons for services, custom robot icons for agents)
- [ ] Color palette documented in `docs/architecture/diagrams/README.md` as a style guide
- [ ] Every diagram has a prose caption explaining what it shows and when to use it

---

## Wave 4: Technical Reference — Backend (Python)

**Agent**: `PythonDeveloper` via `#runSubagent`

**Scope**: Review and update all Python-related documentation and READMEs.

**Files to review/update**:
- `lib/README.md`
- `lib/src/README.md`
- `docs/agentic-microservices-reference.md`
- `docs/implementation/README.md`
- `docs/implementation/truth-layer-agents-guide.md`
- `docs/implementation/truth-layer-api.md`
- `docs/implementation/crud-runtime-resilience.md`
- `docs/implementation/telemetry-envelope-v1.md`
- `docs/implementation/per-agent-azd-deployment.md`
- `docs/implementation/single-rg-deployment-runbook.md`
- `docs/implementation/entra-id-setup.md`
- `docs/implementation/architecture-implementation-plan.md`
- `docs/implementation/c4-component-diagram.md`
- `docs/implementation/compliance-analysis.md`
- `docs/implementation/tested-image-promotion.md`
- All 26 agent app READMEs:
  - `apps/crm-campaign-intelligence/README.md`
  - `apps/crm-profile-aggregation/README.md`
  - `apps/crm-segmentation-personalization/README.md`
  - `apps/crm-support-assistance/README.md`
  - `apps/ecommerce-cart-intelligence/README.md`
  - `apps/ecommerce-catalog-search/README.md`
  - `apps/ecommerce-checkout-support/README.md`
  - `apps/ecommerce-order-status/README.md`
  - `apps/ecommerce-product-detail-enrichment/README.md`
  - `apps/inventory-alerts-triggers/README.md`
  - `apps/inventory-health-check/README.md`
  - `apps/inventory-jit-replenishment/README.md`
  - `apps/inventory-reservation-validation/README.md`
  - `apps/logistics-carrier-selection/README.md`
  - `apps/logistics-eta-computation/README.md`
  - `apps/logistics-returns-support/README.md`
  - `apps/logistics-route-issue-detection/README.md`
  - `apps/product-management-acp-transformation/README.md`
  - `apps/product-management-assortment-optimization/README.md`
  - `apps/product-management-consistency-validation/README.md`
  - `apps/product-management-normalization-classification/README.md`
  - `apps/search-enrichment-agent/README.md`
  - `apps/truth-enrichment/README.md`
  - `apps/truth-export/README.md`
  - `apps/truth-hitl/README.md`
  - `apps/truth-ingestion/README.md`
- `apps/crud-service/README.md`
- `apps/crud-service/src/README.md`
- `apps/README.md`

**Acceptance criteria**:
- [ ] Each agent README follows a consistent template: Purpose, Domain, Endpoints (REST + MCP), Event Subscriptions, Memory Usage, Model Routing (SLM/LLM), Environment Variables, Local Run, Test Coverage
- [ ] `lib/README.md` documents the framework API surface: BaseRetailAgent, AgentBuilder, FoundryAgentInvoker, MemorySettings, adapters, schemas
- [ ] Async patterns documented: `asyncio.gather` for parallel I/O, `FoundryAgentInvoker` tool forwarding, circuit breaker usage
- [ ] Data model contracts (Pydantic schemas) documented with examples
- [ ] CRUD service README documents all REST endpoints, Event Hub publications, and agent-call patterns
- [ ] Integration patterns documented: how agents call CRUD, how CRUD calls agents, Event Hub choreography

---

## Wave 5: Technical Reference — Frontend (TypeScript)

**Agent**: `TypeScriptDeveloper` via `#runSubagent`

**Scope**: Review and update frontend documentation.

**Files to review/update**:
- `apps/ui/README.md`
- `docs/implementation/ui-crud-route-alignment.md`
- `docs/implementation/ui-ux-modernization-review.md`

**Acceptance criteria**:
- [ ] UI README documents: Next.js 15 App Router structure, component catalog, state management (React Query), Tailwind design tokens, deployment to SWA
- [ ] Route structure fully documented with page-level component responsibilities
- [ ] Agent robot overlay system and executive demo flow documented
- [ ] API client architecture (matching ADR-016) described with examples
- [ ] Accessibility compliance (WCAG 2.2 AA) documented

---

## Wave 6: Operations & Governance

**Agent**: `PlatformEngineer` via `#runSubagent`

**Scope**: Review and update all operational and governance documentation.

**Files to review/update**:
- `docs/ops/catalog-search-readiness-503-runbook.md`
- `docs/ops/agc-bisection-2026-04-21.md`
- `docs/governance/README.md`
- `docs/governance/backend-governance.md`
- `docs/governance/frontend-governance.md`
- `docs/governance/infrastructure-governance.md`
- `docs/governance/dependency-audit-wave0.md`
- `docs/governance/repository-hygiene-cleanup.md`
- `docs/governance/security-exception-register.md`
- `docs/governance/security-triage-weekly.md`
- `docs/governance/self-healing-rbac-matrix.md`
- `docs/governance/self-healing-rollout-runbook.md`
- `docs/IMPLEMENTATION_ROADMAP.md`
- `docs/roadmap/README.md`
- All roadmap items `docs/roadmap/001-*.md` through `docs/roadmap/014-*.md`
- `docs/demos/README.md`
- `docs/demos/live-demo-search-enrichment-hitl.md`
- `.infra/README.md`
- `.infra/modules/static-web-app/README.md`
- `.infra/modules/shared-infrastructure/README.md`
- `CONTRIBUTING.md`
- `SECURITY.MD`

**Acceptance criteria**:
- [ ] Deployment procedures current: azd-based provisioning, Flux GitOps for AKS, AGC edge routing, tested image promotion
- [ ] Runbooks tested: catalog-search 503, AGC bisection, self-healing rollout all verified against current infra
- [ ] Monitoring and alerting documented: Application Insights, telemetry envelope v1, health probes
- [ ] Incident response playbook updated with self-healing epic outcomes
- [ ] Security governance current: Entra ID auth, RBAC matrix, Key Vault, secret rotation
- [ ] CI/CD pipeline documentation matches actual workflows (`.github/workflows/`)
- [ ] Environment setup prerequisites verified (Python 3.13, Node 20, uv, azd, Docker)
- [ ] Roadmap items marked as completed/in-progress/planned match actual codebase state

---

## Wave 7: Root-Level README & Documentation Hub

**Agent**: `TechLeadOrchestrator` (self) — final synthesis pass

**Scope**: Update the root README and documentation hub after all specialist waves complete.

**Files to review/update**:
- `README.MD` (root)
- `docs/README.md` (documentation hub)
- `docs/project-status.md`
- `docs/backend_plan.md`
- `docs/crud-features-map.md`
- `mkdocs/README.md`
- `CHANGELOG.md` (verify consistency, do not rewrite)

**Acceptance criteria**:
- [ ] Root README is the definitive 60-second pitch: what, why, how, quick start, architecture diagram, links
- [ ] Documentation hub (`docs/README.md`) serves as index with clear navigation for each audience (developer, architect, operator, business stakeholder)
- [ ] Project status reflects actual state: test count, coverage, deployed services, open issues
- [ ] All cross-references between documents are valid (no broken links)
- [ ] Version/date stamps are consistent across all updated documents
- [ ] `backend_plan.md` and `crud-features-map.md` reflect current implementation (not aspirational)

---

## Cross-Cutting Quality Gates (Apply to ALL Waves)

Every updated document MUST satisfy:

1. **Accuracy** — Content matches current codebase (verify by reading source files before writing)
2. **Visual richness** — Every conceptual section includes at least one visual: Mermaid diagram, table, or flow chart
3. **Consistent formatting** — Markdown heading hierarchy, code block languages specified, tables aligned
4. **Date & version** — Header with `Last Updated: YYYY-MM-DD` and relevant version/PR reference
5. **Audience awareness** — Documents state who they are for (developer, architect, operator, business)
6. **No stale content** — Remove references to features not yet implemented; mark aspirational items clearly as "Planned"
7. **Mermaid theme** — All Mermaid diagrams use the repository-standard theme block:
   ```
   %%{init: {'theme':'base', 'themeVariables': {
     'primaryColor':'#FFB3BA',
     'primaryTextColor':'#000',
     'primaryBorderColor':'#FF8B94',
     'lineColor':'#BAE1FF',
     'secondaryColor':'#BAE1FF',
     'tertiaryColor':'#FFFFFF'
   }}}%%
   ```
8. **Linking** — Documents cross-reference related docs using relative paths
9. **Conciseness** — No filler paragraphs; every sentence adds information

---

## Source-of-Truth References

Before updating any document, agents MUST read relevant source files to ensure accuracy:

| Domain | Source files to read |
|--------|---------------------|
| Agent framework | `lib/src/holiday_peak_lib/agents/`, `lib/src/holiday_peak_lib/agents/memory/` |
| CRUD service | `apps/crud-service/src/` |
| Individual agents | `apps/<agent-name>/src/main.py`, `apps/<agent-name>/src/adapters.py` |
| UI | `apps/ui/app/`, `apps/ui/components/` |
| Infrastructure | `.infra/`, `.github/workflows/`, `k8s/` |
| Configuration | `pyproject.toml`, `azure.yaml`, environment variables |
| Tests | `lib/tests/`, `apps/**/tests/`, `conftest.py` |
| ADRs | `docs/architecture/adrs/` |

---

## Execution Notes

- Process documents **sequentially within each wave** (one file at a time, deep review)
- For each file: **read current content → read relevant source code → identify gaps/inaccuracies → rewrite with full detail**
- Do NOT create new files unless a critical gap is identified (prefer updating existing)
- Do NOT delete existing content without replacement — preserve institutional knowledge
- Mark any document that cannot be fully updated (e.g., missing source code) with a `<!-- TODO: ... -->` comment
- Commit message convention: `docs: update [filename] — [brief reason]`
