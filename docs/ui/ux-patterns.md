# UX patterns / archetypes (ADR-035 §54 / Issue #1059)

> **Status**: Active — landed via Issue #1059. Composition order for each archetype is **locked at v1**. A/B variations are permitted only after ≥ 4 weeks of baseline traffic. Any structural reorder requires an ADR-035 amendment.

The marketing surface of the product is encoded as **four page archetypes**, each composed of components from the F3 component library (Issue #1057, PR #1072) and the F4 token system (Issue #1056, PR #1071). The archetypes are:

| Route | Audience | Cognitive model | Shell |
|---|---|---|---|
| `/` | both / unknown | neutral (Hick's-Law-restricted) | `HomeShell` |
| `/retailers` | retail leadership / operators | warm | `RetailerShell` (route-group layout) |
| `/builders` | platform engineers | cool | `BuilderShell` (route-group layout) |
| `/deploy` | DevOps / pre-sales | cool (slate accent) | `DeployShell` (route-group layout) |

The **persona is a hint, not a gate** (ADR-034 §3) — every archetype renders the full content for both audiences; the persona only nudges the lane-switch CTA.

## Common contract

Every archetype:

1. **No `className` escape hatch on composites**. Density and tone are bound by the parent shell's `data-audience` attribute and the system-token layer.
2. **No raw hex literals in the audience routes**. ESLint rejects them. Colors come from the token system.
3. **No inline `style={{}}` in the audience-route page-level code** (ADR-035 §49 / Issue #1058 L-3). Layout lives inside composites under `components/molecules/` (which are exempt from the `style` rule).
4. **Honesty is enforced at compile time**. `MaturityBadge` is non-optional on every claim-bearing composite. `ConfidenceInterval` is required by the type system on every quantitative `ValueProp`.
5. **One brand, two cognitive models** (ADR-034 §1). Same brand mark across all four archetypes; the audience tokens drive the surface treatment.
6. **en-US only** across all copy and metadata (current repo language policy).

## Archetype A — `/` (audience router, neutral)

**Composition order (locked at v1)**:

1. `<Hero kind="audience-router">` — single headline, one-sentence sub, **two equally-weighted CTAs** ("I'm a retailer" → `/retailers`, "I'm a builder" → `/builders`). No third CTA. No carousel. No autoplay video.
2. `<ValuePropGrid cardinality="three">` — exactly three `<ValueProp>` cards (Hick's-Law cardinality lock).
3. `<Quote>` rendered ONLY when a production-maturity quote exists. Currently omitted.
4. `<CallToAction tone="audience-pair">` — second-pass CTA per NN/g research.

**5-second-test rubric** (target visitor: a person who clicked an Azure-Samples link):

| Question | Visual cue that answers it |
|---|---|
| "What is this?" | The hero headline names "intelligent retail on Azure's agentic platform." |
| "Is this for me?" | Two equally-weighted CTAs labelled "I'm a retailer" / "I'm a builder." |
| "What will the next click do?" | Each CTA names where it goes (the destination route is in the label). |
| "Should I trust this?" | Three value-prop cards each carrying a maturity badge — no synthetic case-study claim above the fold. |

## Archetype B — `/retailers` (warm)

**Composition order (locked at v1)**:

1. `<Hero kind="audience-page">` — outcome-led headline, one-sentence sub naming the problem, single primary CTA + secondary "Book a 20-minute walkthrough."
2. `<ValuePropGrid cardinality="three-to-five">` — every numbered card carries `<ConfidenceInterval>`. No number ships without a citation.
3. `<Comparator kind="before-after">` — three rows comparing manual workflow vs. agent-assisted workflow. `MaturityBadge` is mandatory at the type level on the comparator AND every row.
4. `<AgentCardCluster>` — six representative retail agents linking into `/builders/agents/<slug>`.
5. `<Quote>` rendered only with production-maturity badge. Currently omitted (no production reference).
6. `<CallToAction tone="single">` — book-a-walkthrough CTA.
7. `<CallToAction tone="procurement">` — RFP-tone CTA near the footer with Trust Center link.

**5-second-test rubric**:

| Question | Visual cue that answers it |
|---|---|
| "Will this save me time?" | Hero names a concrete pain ("stop wrestling spreadsheets"); first ValueProp carries an observed time-on-task delta. |
| "Is the number real?" | Every quantitative card renders a `<ConfidenceInterval>` with sample size and methodology. |
| "Have other retailers used this?" | Comparator rows carry maturity badges (design-partner / preview); no card is labelled "production" without evidence. |
| "Where do I start?" | One outcome-CTA in the hero; one walkthrough-CTA mid-page; one procurement-CTA above the footer. Three doors, no decision paralysis. |

## Archetype C — `/builders` (cool)

**Composition order (locked at v1)**:

1. `<Hero kind="audience-page">` — capability-led headline, one-sentence sub, dual CTA ("See architecture →" + "Browse agent catalog →").
2. `<ValuePropGrid cardinality="three-to-five">` — 5 technical capability cards, all qualitative (architecture is described, not numerically claimed).
3. `<CodeBlockCluster>` — three short snippets (call-an-agent, register-MCP-tool, read-three-tier-memory). **Collapsed by default.** Expansion lazy-loads and the canonical-link points at the docs page that owns the snippet (no duplication).
4. `<FeatureMatrix>` — capabilities shipped vs. roadmap. Every row carries `<MaturityBadge>`. No vaporware listed as "available."
5. `<DocsCardCluster>` — direct links into mkdocs sections (`architecture/`, `governance/`, `ops/`).
6. `<CallToAction tone="audience-pair">` — switch lane / try deploy.

**5-second-test rubric**:

| Question | Visual cue that answers it |
|---|---|
| "What's the architecture?" | Hero names the architectural primitives (MCP-only A2A, three-tier memory, AGC blue-green). |
| "How do I call an agent?" | The collapsed `CodeBlockCluster` makes the "call an agent over MCP" snippet a one-click reveal. |
| "What's available today?" | The FeatureMatrix renders an Availability column (available / preview / roadmap / mocked). |
| "Where do I read more?" | Three DocsCards link directly into mkdocs (`architecture/`, `governance/`, `ops/`). |

## Archetype D — `/deploy` (cool, slate accent)

**Composition order (locked at v1)**:

1. `<Hero kind="audience-page">` — operational headline ("Deploy agentic retail to your Azure tenant"), sub names prerequisites (Azure subscription, Entra tenant), primary CTA "Start" + secondary "Open the canonical Azure cost calculator."
2. `<DeployStepCluster>` — 5 steps (sign in, pick subscription, name deployment, **review estimated cost**, launch). Steps 1 and 4 are stateful (`stateful: true`); the rest are server-rendered.
3. `<FeatureMatrix showRegion>` — what gets deployed, in what region, what is mocked vs. real (synthetic data on first run).
4. `<DocsCardCluster>` — what to do after deploy, rollback procedure, tear-down.
5. `<CallToAction tone="single">` — start CTA at the bottom (mirror of the hero CTA).

**Cost-preview legal handling (step 4)**: the cost is rendered as a range with the explicit non-contractual disclaimer ("estimated, varies by region; not a contractual quote"). The hero secondary CTA is a more-prominent link to the canonical Azure cost calculator than the in-page number.

**5-second-test rubric**:

| Question | Visual cue that answers it |
|---|---|
| "What do I need before I start?" | Hero sub names prerequisites (Azure subscription, Entra tenant). |
| "How many steps?" | The cluster renders 5 numbered steps; each carries a one-sentence summary. |
| "How much will it cost?" | Step 4 carries the disclaimer; the hero secondary CTA points to the canonical Azure cost calculator. |
| "What if it breaks?" | DocsCardCluster surfaces the rollback runbook directly, alongside the post-deploy and tear-down runbooks. |

## Anti-patterns rejected

- **No carousel of "trusted by" logos.** No archetype renders a logo wall.
- **No autoplay video hero.** Heroes are text + CTAs.
- **No scroll-jacking.** Section transitions follow the document flow.
- **No third CTA on `/`.** Hick's-Law cardinality lock.
- **No value-prop card lacking a citation when it carries a number.** Compile-time enforced.
- **No `className` escape hatch on composites.** Tone is bound by audience tokens.
- **No `style={{}}` prop in audience-route page-level code.** Layout lives in composites.
- **No raw hex literals in audience routes.** Colors come from the token system.

## Cardinality and rhythm rules

| Slot | Cardinality | Rule |
|---|---|---|
| `/` `<ValuePropGrid>` | exactly 3 | Hick's-Law cardinality lock at the audience router. |
| `/retailers` `<ValuePropGrid>` | 3–5 | Runtime-checked by `<ValuePropGrid cardinality="three-to-five">`. |
| `/retailers` `<AgentCardCluster>` | exactly 6 | Documented above; no compile-time check (cluster is a flat list). |
| `/builders` `<ValuePropGrid>` | 3–5 | Runtime-checked; we ship 5 today. |
| `/builders` `<CodeBlockCluster>` | exactly 3 | Documented above. |
| `/deploy` `<DeployStepCluster>` | exactly 5 | Documented above. Two of the five are stateful. |
| `<FeatureMatrix>` | 3–10 rows | No hard cap; readability falls off above ~10. |

## A/B variation policy

Composition order is **locked at v1**. A/B variations are permitted only after ≥ 4 weeks of baseline traffic on the locked composition. Reasoning: with no baseline, A/B traffic produces noise, not signal.

When an A/B variation is proposed, the proposing PR must (1) cite the baseline metrics it intends to beat, (2) state the hypothesis under test, (3) state the success threshold, and (4) include rollback criteria.

Any structural reorder (adding a new section, removing one, swapping two) requires an ADR-035 amendment, not just an A/B test.

## Metadata shape per archetype

Metadata is declared via Next.js 16 `metadata` API in each `page.tsx`. Per ADR-034:

| Route | OG variant | Title pattern | Description pattern |
|---|---|---|---|
| `/` | `audience: neutral` | "Holiday Peak Hub — Intelligent retail on Azure" | Pick-your-lane summary. |
| `/retailers` | warm | "Holiday Peak Hub for Retailers — outcomes, not dashboards" | Outcome-led summary citing maturity. |
| `/builders` | cool | "Holiday Peak Hub for Builders — architecture & contracts" | Capability-led summary citing primitives. |
| `/deploy` | cool (slate) | "Deploy Holiday Peak Hub to your Azure tenant" | Prerequisites + first-run summary. |

Metadata never mixes warm and cool — each archetype's OG variant matches its audience.

## References

- ADR-034 — Audience-segmented IA — [`docs/architecture/adrs/adr-034-audience-segmented-ia.md`](../architecture/adrs/adr-034-audience-segmented-ia.md)
- ADR-035 — UI design system — [`docs/architecture/adrs/adr-035-ui-design-system.md`](../architecture/adrs/adr-035-ui-design-system.md)
- Design tokens — [`docs/ui/design-tokens.md`](./design-tokens.md)
- CSS architecture — [`docs/ui/css-architecture.md`](./css-architecture.md)
- Five-second test — [`docs/governance/five-second-test.md`](../governance/five-second-test.md)
