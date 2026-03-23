# Live Demo Runbook: Search, Enrichment, and HITL

**Last Updated**: March 23, 2026  
**Audience**: Demo operators and stakeholder-facing presenters  
**Target UI**: https://blue-meadow-00fcb8810.4.azurestaticapps.net/

---

## Preconditions

Before starting, confirm:

1. **Target URL is reachable**: open `https://blue-meadow-00fcb8810.4.azurestaticapps.net/`.
2. **Session state is known**:
   - If the app opens at login, continue with sign-in.
   - If you are already signed in, continue to Flow A.
3. **Auth path for demo**:
   - Open `https://blue-meadow-00fcb8810.4.azurestaticapps.net/auth/login`.
   - If mock role buttons are visible, sign in as **Staff** to access review workflows.
   - If Microsoft sign-in is shown, sign in with the operator account that has staff access.
4. **Operator setup**:
   - Use a clean browser tab (or private window) to keep the flow consistent.
   - Keep one extra tab ready for `/staff/review`.
5. **Catalog-search AI Search runtime wiring**:
    - Confirm deployment env vars are present:
       - `kubectl set env deployment/ecommerce-catalog-search-ecommerce-catalog-search --list -n holiday-peak | Select-String "AI_SEARCH_ENDPOINT|AI_SEARCH_INDEX|AI_SEARCH_AUTH_MODE|CRUD_SERVICE_URL"`
    - If env vars were changed, wait for rollout:
       - `kubectl rollout status deployment/ecommerce-catalog-search-ecommerce-catalog-search -n holiday-peak --timeout=180s`

---

## Flow A: Agentic Search Superiority Demo

**Goal**: Show intelligent search behavior and side-by-side comparison signals.

| Step | Operator action | Expected audience outcome |
|---|---|---|
| A1 | Open `/search`. | Search screen is visible with mode controls and search input. |
| A2 | Click **Run agent-friendly query** (or search for `laptop`). | Results populate for a realistic intent-heavy query. |
| A3 | Point out the **Intelligent Search** mode chip and intent panel content. | Audience sees that the result view includes intent and subquery context. |
| A4 | Show the intelligent-vs-keyword scorecard block on the same page. | Audience sees a direct comparison view for intelligent and keyword rankings. |
| A5 | Toggle search mode preference (if needed) and rerun the same query. | Audience observes mode-aware behavior on identical input. |
| A6 | Click **View search trace**. | Audience sees a trace entry/view for this search run. |

Presenter notes:
- Keep the query text identical when comparing modes.
- Describe only what is visible in the UI (mode indicator, intent display, scorecard, trace link).

---

## Flow B: Product Enrichment Demo

**Goal**: Show enriched product detail experience from discovery to detail context.

| Step | Operator action | Expected audience outcome |
|---|---|---|
| B1 | From search results, open one product detail page. | Product detail page loads for the selected item. |
| B2 | Highlight the **Agent Enriched** badge near the product header. | Audience sees that the product is marked as enriched in the UI. |
| B3 | Highlight the **Enriched description** card. | Audience sees enriched narrative content on the PDP. |
| B4 | Show **Use case** tags and related product rails (complements/substitutes), when present. | Audience sees contextual enrichment artifacts on the same page. |
| B5 | Run the use-case fit evaluation panel (enter a practical use case and submit), if available. | Audience sees a fit verdict-style response with reasoning bullets. |

Presenter notes:
- If one product has limited enrichment, open a second product from search to keep the demo moving.
- Keep focus on visible artifacts (badge, enriched description, contextual rails, fit response panel).

---

## Flow C: HITL Review Workflow Demo

**Goal**: Show staff review queue and approval/rejection actions.

| Step | Operator action | Expected audience outcome |
|---|---|---|
| C1 | Open `/staff/review`. | Audience sees **AI Review Queue** with pending count and summary cards. |
| C2 | Apply one filter (category/source/confidence) and clear it. | Audience sees queue filtering behavior in real time. |
| C3 | Open one queue item (product review detail). | Audience sees proposed attributes list for a specific product. |
| C4 | Approve or reject one pending proposal. | Audience sees status transition for the acted proposal. |
| C5 | Show **Audit History** section on the same page. | Audience sees review actions reflected in timeline/audit context. |
| C6 | Return to queue and show updated pending counts. | Audience sees queue-level impact after review action. |

Presenter notes:
- If the queue is empty, state that no pending proposals are currently available and proceed to troubleshooting checks.
- Use single-item actions first; use bulk actions only if there are multiple pending items.

---

## End-to-End Combined Talk Track (Short Script)

1. Start on `/search` and run an intent-rich query to show intelligent mode indicators and comparison scorecard.
2. Open one returned product and call out the visible enrichment artifacts on the PDP.
3. Transition to `/staff/review` to show how proposed changes are reviewed by staff.
4. Complete one review action and show audit/totals update.
5. Close by restating the observable chain: **search context → enriched product view → human review control**.

---

## Troubleshooting Quick Checks

Run these checks if any flow fails during live demo:

1. **Root UI reachable**
   - Open `https://blue-meadow-00fcb8810.4.azurestaticapps.net/`.
   - Expected: HTTP 200 and the storefront home page renders.

2. **API proxy health reachable**
   - Open `https://blue-meadow-00fcb8810.4.azurestaticapps.net/api/health`.
   - Expected: HTTP 200.

3. **Catalog API path reachable**
   - Open `https://blue-meadow-00fcb8810.4.azurestaticapps.net/api/products?limit=1`.
   - Expected: HTTP 200 with a minimal product payload.

4. **Auth mode clarity**
   - Open `/auth/login` and confirm which login method is active (mock role selector or Microsoft sign-in).
   - Expected: one clear sign-in path is visible and actionable.

5. **HITL route access**
   - Open `/staff/review` directly after sign-in.
   - Expected: review queue renders; if unauthorized, re-authenticate with a staff-capable account/role.

6. **Search fallback handling**
   - If search warning appears, click **Retry search** and rerun the same query.
   - Expected: results and mode indicators repopulate.

7. **AI Search runtime verification**
   - Invoke agent API directly:
     - `python -c "import json,urllib.request; data=json.dumps({'query':'laptop','limit':5,'mode':'intelligent'}).encode(); req=urllib.request.Request('https://holidaypeakhub405-dev-apim.azure-api.net/agents/ecommerce-catalog-search/invoke', data=data, headers={'Content-Type':'application/json'}); resp=urllib.request.urlopen(req, timeout=25); print(resp.status); print(resp.read().decode()[:500])"`
   - If response still contains mock placeholders after env update, a new service image rollout is still required for adapter code changes.

8. **Seed HITL queue when empty**
    - If `/staff/review` is empty, publish one queue item:
       - `python scripts/ops/seed_hitl_queue.py --auth-mode identity --namespace holidaypeakhub405-dev-eventhub --entity-id prd-electronics-001 --field-name material --proposed-value titanium --confidence 0.42 --product-title "Aurora X1 Laptop" --category-label "Electronics"`
    - Then refresh `/staff/review`.
    - Use `--dry-run` first to preview payload without publishing.
