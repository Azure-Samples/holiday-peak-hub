# Intelligent Search and Agent Comparison

## Purpose

Use this walkthrough to test the current search experience, including keyword mode, intelligent mode, fallback behavior, and the popup comparison entry points.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | Public or signed-in customer |
| Main navigation access | `Search Demo` link in the top navigation, or the search box in the header |
| Primary route | `/search` |
| Agent comparison entry points | `Open popup comparison`, `Agent` button in the header, or `/search?agentChat=1` |
| Working status | Implemented and working |

## Exact Click Path

1. Click `Search Demo` in the top navigation.
2. Type a search query in `Search products...`.
3. Press Enter.
4. Choose a mode in the `SearchModeToggle` control.
5. Watch the result cards, intent panels, and comparison scorecard update.
6. Click any result card to open the product detail page.

## Recommended Demo Flow

1. Open `/search`.
2. In the demo action bar near the top of the page, click `Run agent-friendly query`.
3. Watch the page populate with the built-in `laptop` example.
4. Confirm the screen shows these core areas:
   - `Search` page title
   - `SearchInput`
   - search mode selector
   - search mode indicator
   - intent classification area
   - result list

## How to run a manual search

1. Click inside the `Search products...` field.
2. Type a natural-language query such as `best lightweight laptop for travel`.
3. Press Enter.
4. Confirm the URL changes to `/search?q=...`.
5. Wait for the search results section to render.

## How to switch search modes

1. Look for the mode toggle directly under the main search box.
2. Select each mode one at a time:
   - `auto`
   - `keyword`
   - `intelligent`
3. After each selection, wait for the results to refresh.
4. Confirm the page shows a status pill similar to:
   - `Intelligent Search • Source: Agent API`
   - `Keyword Search • Source: CRUD Catalog`

## What to look for in intelligent mode

1. Confirm the `IntentClassificationDisplay` appears.
2. Confirm the `IntentPanel` appears when the backend returns intent or subquery data.
3. If reranking is active, the page should briefly show `Reranking baseline results in the background...`.
4. Confirm the `SearchComparisonScorecard` appears after both baseline and reranked results are available.

## How fallback behaves

1. Keep the mode on `intelligent`.
2. If the agent path is unavailable, the page should continue showing results from CRUD.
3. In that case, confirm you see the warning box `Intelligent mode fell back to catalog`.
4. If the proxy itself fails, confirm you see:
   - a warning explaining catalog search is unavailable
   - a `Retry search` button

## How to use the popup comparison path

1. From the top action bar on the search page, click `Open popup comparison`.
2. You can also click the `Agent` pill in the site header.
3. Both paths route to `/search?agentChat=1`.
4. Use that variant when you want to demo the agent-focused search entry point without leaving the search experience.

## How to inspect search trace links

1. Run any non-empty search.
2. Look for the trace link below the action bar.
3. If the response includes a trace ID, the link label becomes `View search trace`.
4. If no trace ID is returned, the fallback label is `View Agent Activity`.
5. Click the link to move into the admin tracing surface.

## Success checklist

| Check | Expected result |
| --- | --- |
| Query submission | URL updates to `/search?q=...` |
| Mode change | Search source and behavior update |
| Intelligent mode | Intent UI and comparison scorecard appear when data is available |
| Fallback mode | Results continue from CRUD with warning copy |
| Result selection | Clicking a result opens the product page |

## Notes about personalization and context

If the user is signed in, the search request includes contextual fields such as user ID, session ID, stage, and recent query history. The user does not need to do anything special in the UI for that behavior.
