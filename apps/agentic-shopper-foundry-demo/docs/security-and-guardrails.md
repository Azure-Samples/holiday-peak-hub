# Security and guardrails

This demo is scoped intentionally so it can be shown safely.

## What we enforce in the demo

- Scope is explicit: no checkout, no refunds, no order changes.
- Actions are only available through the tool surface (no direct API reach-through).
- Context injection is small and predictable (SKU/category/segment), not a raw data dump.

## What changes for a real customer deployment

- Run under Managed Identity / workload identity.
- Put tool endpoints behind APIM + private networking.
- Add role-based access (ex: support agent vs shopper).
- Add content safety and policy checks at the API boundary.
- Log traces and tool calls to a central store.
