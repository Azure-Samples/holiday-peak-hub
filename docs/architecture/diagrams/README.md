# Architecture Diagrams

Canonical diagram index for Holiday Peak Hub.

## C4 Draw.io Diagrams

| Diagram | Viewpoint | Purpose |
|---|---|---|
| `c4-system-context.drawio` | C4 Context | External actors, channels, and system boundary |
| `c4-container-azure-runtime.drawio` | C4 Container | Azure runtime composition across edge, AKS, and platform services |
| `c4-component-summary.drawio` | C4 Component | Service grouping and high-level internal composition |
| `c4-component-detailed.drawio` | C4 Component | Detailed component/service relationships |

## Sequence Diagrams (Mermaid)

| Diagram | Domain | Focus |
|---|---|---|
| `sequence-catalog-search.md` | E-commerce | Search flow with model routing and enrichment |
| `sequence-inventory-health.md` | Inventory | Health monitoring, anomaly detection, and remediation |
| `sequence-returns-support.md` | Logistics/CRM | Returns evaluation and resolution flow |

## Usage Guidelines

- Keep C4 diagrams in `.drawio` format as the architecture source of truth.
- Keep runtime interaction flows in Mermaid sequence files.
- Update this index whenever diagram files are added, removed, or renamed.
- Keep diagram naming stable to avoid broken links in architecture docs.

## Related Docs

- `docs/architecture/architecture.md`
- `docs/architecture/ADRs.md`
- `docs/architecture/components.md`
- `docs/architecture/playbooks/README.md`
