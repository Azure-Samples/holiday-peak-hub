# Architecture

This demo uses the same pattern we use in customer builds: a clean UI surface, a small orchestration layer, and a tool surface that represents the customer’s real systems.

## Layers

1) UI (static)
- `static/index.html`
- Stage-style flow: category → product → chat
- A trace panel that tells the story while you demo

2) API
- `src/server.py` (FastAPI)
- Receives page context (product, category, segment)
- Starts a request trace and returns both the answer and the “what happened” timeline

3) Agent runtime
- `src/agent.py`
- Azure AI Foundry Agents provides threads + hosted runtime
- Microsoft Agent Framework wires instructions and tool calling

4) Tool surface
- `src/tools.py`
- In this repo: backed by `sample_data/products.json`
- In a customer deployment: backed by their catalog, OMS, CRM, and personalization APIs

## Why the trace panel matters

Customers don’t just want the answer. They want to see the system behaving in a controlled way:
- what context was used
- which actions were called
- what was blocked by scope

That’s what makes this demo feel “CP-ready,” even though it’s still a demo.
