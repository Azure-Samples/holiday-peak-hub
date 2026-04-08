# UI/UX Modernization Review

**Last Updated**: April 3, 2026  
**Status**: Draft for review

## Objective

This review maps the current Next.js UI surface to a stronger product direction for customer, staff, and admin experiences. The goal is not a cosmetic refresh. The goal is to make the product feel like three coherent systems:

- a modern retail storefront for customers,
- a fast decision workbench for staff,
- an explainable control plane for admin and AI operations.

The recommendations below are grounded in the current route inventory under [../../apps/ui/app/page.tsx](../../apps/ui/app/page.tsx), [../../apps/ui/app/search/page.tsx](../../apps/ui/app/search/page.tsx), [../../apps/ui/app/staff/review/page.tsx](../../apps/ui/app/staff/review/page.tsx), [../../apps/ui/app/admin/agent-activity/page.tsx](../../apps/ui/app/admin/agent-activity/page.tsx), and the shared shell components in [../../apps/ui/components/templates/MainLayout.tsx](../../apps/ui/components/templates/MainLayout.tsx) and [../../apps/ui/components/navbar-1.tsx](../../apps/ui/components/navbar-1.tsx).

## Executive Summary

1. The current UI is functionally broad but structurally mixed. Customer commerce, staff operations, admin tooling, and demo routes currently share too much shell and navigation language.
2. The highest-value UX investment is in customer search, product detail, cart, checkout, and orders; the highest-risk internal investment is in staff review/requests and admin trace observability.
3. The product should use dynamic and exploratory UI where it improves discovery and comprehension, but it should remain explicit and audit-friendly anywhere money, inventory, approvals, or configuration are being committed.
4. SVG visualization, animation, and drag interactions are good fits for product discovery, pipeline monitoring, and trace inspection. They should never be the only way to act on the interface.

## Validation Sources

### Internal product evidence

- [../../apps/ui/app/page.tsx](../../apps/ui/app/page.tsx)
- [../../apps/ui/app/dashboard/page.tsx](../../apps/ui/app/dashboard/page.tsx)
- [../../apps/ui/app/search/page.tsx](../../apps/ui/app/search/page.tsx)
- [../../apps/ui/app/product/ProductPageClient.tsx](../../apps/ui/app/product/ProductPageClient.tsx)
- [../../apps/ui/app/checkout/page.tsx](../../apps/ui/app/checkout/page.tsx)
- [../../apps/ui/app/staff/review/page.tsx](../../apps/ui/app/staff/review/page.tsx)
- [../../apps/ui/app/staff/requests/page.tsx](../../apps/ui/app/staff/requests/page.tsx)
- [../../apps/ui/app/admin/agent-activity/page.tsx](../../apps/ui/app/admin/agent-activity/page.tsx)
- [../../apps/ui/components/templates/MainLayout.tsx](../../apps/ui/components/templates/MainLayout.tsx)
- [../../apps/ui/components/navbar-1.tsx](../../apps/ui/components/navbar-1.tsx)

### External guidance used in this review

- [MDN HTML](https://developer.mozilla.org/en-US/docs/Web/HTML)
- [MDN CSS](https://developer.mozilla.org/en-US/docs/Web/CSS)
- [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [WAI-ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- [web.dev Core Web Vitals and animation guidance](https://web.dev/explore/)
- [web.dev animation guidance](https://web.dev/explore/animations)
- [Tailwind utility-first guidance](https://tailwindcss.com/docs/styling-with-utility-classes)
- [Material 3 tabs](https://m3.material.io/components/tabs/overview)
- [Material 3 navigation guidance](https://m3.material.io/components/navigation-drawer/overview)
- [Carbon data table usage](https://carbondesignsystem.com/components/data-table/usage/)
- [Carbon search usage](https://carbondesignsystem.com/components/search/usage/)
- [Carbon UI shell left panel](https://carbondesignsystem.com/components/UI-shell-left-panel/usage/)
- [Shopify Polaris index filters](https://polaris-react.shopify.com/components/selection-and-input/index-filters)
- [Shopify Polaris index table](https://polaris-react.shopify.com/components/tables/index-table)
- [Shopify Polaris navigation](https://polaris-react.shopify.com/components/navigation)

Note: the Polaris React pages are deprecated as implementation packages, but they still provide useful interaction patterns for commerce back-office list management. Reuse the concepts, not the package.

## Current UI Findings

### 1. The shell is still demo-first

The shared navigation currently exposes demo-oriented destinations such as search demo, product demo, and agent popup alongside core app routes. That makes the product feel like a showcase instead of a role-aware application.

### 2. Persona boundaries are too weak

Customers, staff, and admin operators should not share the same primary navigation model. The information density, safety posture, and navigation depth are fundamentally different.

### 3. The product already has useful fallback behavior, but the UX does not always explain it

Search, enrichment, tracing, and checkout already surface technical availability states. Those states should evolve from plain alerts into product-grade status language: estimated, degraded, held, locked, awaiting review, and recovered.

### 4. Operational surfaces need stronger list and decision patterns

Review queues, requests, logistics, and admin lists are functional, but they need better filtering, saved views, bulk actions, drill-down affordances, and side-panel detail patterns.

### 5. Dynamic visuals should be used more selectively

The home graph already points in the right direction, but other areas that would benefit more from SVG-driven visualization are still mostly rendered as basic cards and tables: trace waterfalls, pipeline states, return lifecycles, and evidence diffs.

## Product Direction

### Shell strategy

- **Customer shell**: editorial, visual, lightweight. Top navigation plus contextual search. Mobile-first bottom actions for cart, orders, and profile.
- **Staff shell**: denser workbench. Desktop-first left rail with queue counts, saved views, breadcrumbs, and a persistent action bar. Mobile should use a modal navigation sheet and stack detail panels vertically.
- **Admin shell**: control-plane shell. Expanded navigation rail on desktop, modal rail on smaller screens, persistent environment indicator, trace/evaluation quick search, and strong breadcrumbing.

### Interaction strategy

- **Exploratory interactions** belong in home, category browsing, search, recommendations, and analytics read views.
- **Controlled interactions** belong in checkout, approvals, refunds, logistics status changes, schema edits, and config changes.
- **Hybrid interactions** belong in product detail, cart, order tracking, and dashboards, where live intelligence can update but commitments must still be explicit.

### Visual strategy

- Keep the existing ocean/cyan/lime direction, but evolve it into a sharper token system with stronger contrast tiers, not a flat card-on-page look.
- Use SVG and canvas selectively for graph exploration, pipeline diagrams, waterfalls, timeline states, and evidence comparison.
- Make motion meaningful: reveal hierarchy, show change over time, and explain system state. Avoid decorative motion that adds latency or ambiguity.

## Investment Priority

| Priority | Surface family | Reason |
| --- | --- | --- |
| Highest | Customer commerce core | Direct conversion, trust, and support-cost impact |
| Very high | Staff review, requests, logistics | High exception-handling cost and human decision quality |
| High | Admin observability and truth operations | Required to operate agentic features safely and explainably |
| Medium | Account and self-service | Important for retention, but less differentiated |
| Selective | Redirect/demo/helper routes | Should be simplified or absorbed into canonical flows |

## View-by-View Recommendations

## Customer Commerce

- **`/` Home**: Keep the interactive product graph idea, but reframe it as an editorial storefront canvas. On desktop, let users drag and pin product clusters, then mirror the current selection in a right-hand summary rail with reasons such as trending, gift-ready, low inventory risk, or high margin. On mobile, replace freeform dragging with swipeable story shelves and one-tap cluster presets.

- **`/categories`**: Turn this into a category atlas instead of a plain list. Use large image-backed cards, product counts, seasonal cues, and short category descriptors. Mobile should prioritize two-column cards with sticky jump chips.

- **`/category/[slug]`** and **`/category`**: The best fit is a modern browse workspace with a sticky filter rail on desktop and a bottom-sheet filter experience on mobile. Promote 2-3 high-value filters, show applied filter chips clearly, and let users switch between grid, compact list, and comparison-friendly card modes.

- **`/search`**: This should become a dual-lane search experience. The left lane should show the AI interpretation of intent, subqueries, and why the current mode was chosen. The main lane should remain deterministic and result-oriented, with comparison scorecards, result counts, and a visible fallback explanation when the agent path is unavailable. On desktop, offer a dockable comparison tray. On mobile, collapse the AI lane into a summary drawer.

- **`/product`** and **`/product/[id]`**: Use a narrative product detail layout with a strong media gallery, sticky commitment buy box, explainable enrichment tabs, and a related-products rail that behaves like a smart accessory tray. Show AI reasoning only where it answers a real customer question such as fit, use case, or compatibility. Attribute evidence should be readable without looking like a raw trace dump.

- **`/cart`**: Replace the current mobile-unfriendly table bias with card stacks on small screens and a split review/summary layout on desktop. Add optimistic updates, undo for removals, and a persistent commitment strip that explains whether pricing and inventory are estimated or currently held.

- **`/checkout`**: The strongest pattern is a guided checkout with a clear stepper, order summary rail, and a commitment-state ribbon that distinguishes estimated, held, and locked states for inventory, ETA, and price. Desktop can show a parallel inventory assistant panel. Mobile should reduce this to a collapsible risk summary and a sticky place-order footer. Add a review step before payment confirmation.

- **`/orders`**: Use an order index that behaves more like a resource list than a plain table. Make each order row a summary card with status, ETA, return eligibility, and clear next actions. Add filters for status and date range.

- **`/order/[id]`**: Present this as a lifecycle page with a timeline, shipment blocks, item-level status, and a dedicated return action area. Use SVG or thin timeline graphics to show order, ship, deliver, return, refund, and restock states.

- **`/wishlist`**: Make this a real saved-items workspace with price-drop badges, back-in-stock signals, and quick-add-to-cart actions. If persistent wishlist support is not ready, do not present it as a finished destination. Mark it as preview or move it behind a feature flag.

- **`/shop`**, **`/deals`**, and **`/new`**: These should not be silent redirects. Either promote them into clear landing pages with curated merchandising, or collapse them into canonical browse/search routes and remove them from user-visible navigation.

## Account And Auth

- **`/auth/login`** and **`/auth/signup`**: The login surface should be calm, low-noise, and explicit about whether the user is entering a production auth flow or a developer mock flow. Mock-role controls should live in a clearly separated developer panel, not in the main auth rhythm.

- **`/profile`**: Rework this as a task-based settings page instead of a tabbed dump of partially unavailable sections. Personal info, preferences, security, addresses, and payment methods should each have obvious completion states. Unsupported sections should be hidden or shown as roadmap items, not as dead tabs.

- **`/dashboard`**: This route currently behaves like a demo harness for personalization. It should either become a true customer home with orders, saved items, recommendations, and account tasks, or move under a demo/lab namespace so it stops competing with production-facing navigation.

- **`/logout`**: Keep it simple, but make the transition explicit. A short signing-out state with clear destination text is sufficient.

## Staff Operations

- **`/staff/sales`**: This should be a performance cockpit, not just KPI cards. Add sparklines, comparison periods, product drill-down, and anomaly flags. Desktop can support panel rearrangement for read-only personalization, but the default layout should remain stable.

- **`/staff/review`**: Rebuild the review queue as an index-table pattern with saved views, promoted filters, bulk actions, and an action bar. Confidence and source should be rendered as scan-friendly badges. Mobile should collapse into stacked review cards with key metadata and a one-tap open-detail action.

- **`/staff/review/[entityId]`**: The ideal pattern is a split decision workbench. Use a left column for product and proposal summary, a center area for attribute diffs and evidence, and a right column for the decision composer and audit trail. On mobile, stack these as summary, diff, evidence, and action sections in that order.

- **`/staff/requests`**: This should become a unified exception inbox for returns and support cases. Use queue health chips, grouped views, and clear next-step actions. Avoid drag-only status changes; if a board view is introduced on desktop, every move must also be available through explicit buttons or menus.

- **`/staff/logistics`**: Move from a plain searchable table to a logistics monitor with a map or route-context strip, shipment timeline states, carrier cards, and fast filtering by status, exception type, and urgency. Tracking numbers should be actionable links, not inert text.

## Admin And Observability

- **`/admin`**: Turn the admin landing page into a control-plane home with domain health, recent incidents, favorite tools, and recommended actions. Separate routine operational monitoring from configuration and schema tools.

- **`/admin/agent-activity`**: This should feel like an observability cockpit. Use a dense shell with sticky time-range controls, anomaly summaries, trace density indicators, and AI/model split cards that are trend-aware instead of count-only. Mobile should degrade to prioritized cards and compact lists, not horizontal table overflow.

- **`/admin/agent-activity/[traceId]`**: Lean into SVG for this route. The best-fit UX is a trace investigation page with a visual waterfall, expandable event timeline, tool-call evidence drawer, and copy/export affordances. Desktop can show graph plus details side-by-side. Mobile should switch to a linear event stream.

- **`/admin/agent-activity/evaluations`**: Position this as an evaluation lab. Show model/version comparisons, trend direction, regression callouts, and clickable metric cards that reveal representative examples or slices of failed evaluations.

- **`/admin/enrichment-monitor`**: This should become a pipeline board, not just a card set. Use a stage-by-stage SVG diagram with clickable nodes for pending review, approved, rejected, and blocked states. Each stage should open a filtered list or detail slice.

- **`/admin/enrichment-monitor/[entityId]`**: Use a tri-pane evidence view with attribute diff, media/evidence gallery, and reasoning summary. Add confidence context per field, not just at the record level. This route should explain why the decision exists, not just expose raw output.

- **`/admin/truth-analytics`**: The right archetype is an analytics storyboard. Use completeness charts, throughput trends, and a pipeline-flow SVG that can highlight bottlenecks and drill into category-specific quality issues. Keep charts responsive and readable at 200% zoom.

- **`/admin/config`**: Use grouped settings sections, sticky save and reset affordances, inline help text, and a change-impact preview. Configuration pages should feel safe and reversible, not experimental.

- **`/admin/schemas`**: This should be a schema builder with structured editing, field grouping, validation, and product preview. Desktop can support side-by-side schema and sample product preview. Mobile should fall back to accordion sections and validation-first editing.

- **`/admin/ecommerce/products`** and **`/admin/[domain]/[service]`**: Keep the shared service dashboard shell, but require a service-specific overview, recent failures, queue health, and core actions. Generic dashboards are acceptable only as a frame, not as the final user experience.

## Redirect And Agent Surfaces

- **`/agents/product-enrichment-chat`**: Replace silent redirect behavior with a brief handoff page or in-context sheet that tells the user what is opening and what context is being transferred.

- **Other redirect-style routes**: Any route that exists only to forward the user should either become a true page or disappear from the public navigation structure.

## Motion, SVG, And Drag Guidance

### Good uses of SVG and motion

- Home product constellation and category clustering
- Search comparison scorecards and semantic-result relationships
- Order, return, and refund timelines
- Review diff connectors between current and proposed values
- Enrichment pipeline stage diagrams
- Trace waterfalls, span trees, and retry/recovery flows

### Good uses of desktop-enhanced drag behavior

- Repositioning the home discovery graph
- Reordering a comparison tray or saved analyst panels
- Rearranging read-only dashboard modules for personal preference

### Rules for safe interaction design

- Any drag interaction must also support click, tap, keyboard, or menu-driven alternatives to satisfy WCAG 2.2 dragging and keyboard guidance.
- Motion should use transform and opacity where possible and respect `prefers-reduced-motion`.
- No operationally critical interaction should depend on hover-only affordances.
- Touch targets should remain at least 24x24 CSS pixels at minimum and preferably 44x44 on primary actions.

## Delivery Waves

1. **Shell split and route cleanup**: separate customer, staff, admin, and demo navigation; remove silent redirects from the main UX.
2. **Commerce core**: redesign search, product detail, cart, checkout, and orders around commitment states and explainable AI.
3. **Staff workbench**: rebuild review queue/detail, requests, and logistics around index-table and decision-workbench patterns.
4. **Admin control plane**: modernize agent activity, trace detail, enrichment monitor, truth analytics, config, and schema management.
5. **Polish and validation**: motion tuning, responsive hardening, accessibility audits, and Core Web Vitals optimization.

## Review Checklist

- Does each shell clearly match one persona and one mental model?
- Are exploratory AI interactions separated from binding business actions?
- Do mobile layouts remove horizontal scrolling from customer-critical flows?
- Are status states expressed in product language instead of raw technical failure language?
- Do staff and admin tables support filtering, bulk action, drill-down, and keyboard operation?
- Are SVG and motion features explainable, optional, and reduced-motion safe?

## Recommendation

The strongest next move is not a page-by-page restyle. It is a structural reset:

- separate the shells,
- redesign the commerce core around trust and commitment states,
- redesign staff/admin around workbench and control-plane patterns,
- then add dynamic SVG, motion, and desktop-only enhancements where they improve comprehension.

That sequence will produce a UI that feels modern because it is better organized and more legible, not just because it animates more.