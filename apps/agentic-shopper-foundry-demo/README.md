# Agentic Shopper — Customer Demo Kit (Foundry + Agent Framework)

This repo is my customer-ready Agentic Shopper demo. It’s built to feel like a real retail embedding (PLP → PDP → Chat), and it explains itself while you run it.

The goal is simple: in a customer meeting (example: Patagonia), the demo should look polished and the system should be easy to follow.

## What’s included

- **FastAPI backend** that hosts the UI and a single `/api/chat` endpoint
- **Azure AI Foundry Agent** runtime wired through **Microsoft Agent Framework (Python)**
- **Tool calls** that look like real commerce integrations (ranking, availability, personalization)
- **A stage UI** (category list → product select → chat) that resembles PLP/PDP behavior
- **A “What just happened” panel** that shows context injection, guardrail checks, and tool calls in real time
- **Sample Patagonia-style catalog** in `sample_data/products.json` (swap with your customer’s catalog)

## Quickstart

### Prereqs
- Python 3.10+
- Azure CLI for local auth (`az login`)
- An Azure AI Foundry Project with a model deployment (ex: `gpt-4.1-mini`)

### Setup
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# edit .env with your Foundry project + deployment

python run_server.py
```

Open `http://localhost:8000`.

## UI tour (what to point out on the call)

- **Left (Stage)**: pick a category and select a product. This is the “page context” the agent receives.
- **Middle (Chat)**: ask questions and get recommendations.
- **Right (What just happened)**: shows the system steps:
  - request came in
  - scope/guardrail check
  - context injected (product/category/segment)
  - which actions fired (tool calls)

This is the piece that makes the demo customer-friendly.

## How it works

- `src/agent.py` creates a long-lived Foundry Agent and registers tools.
- `src/server.py` receives UI context (product/category/segment), adds a short context capsule, then runs the agent.
- `src/telemetry/trace.py` captures demo-friendly trace events.
- `src/tools.py` contains demo tools backed by the sample catalog. In a customer engagement you replace these with real service calls.

## Swap the demo tools for real systems

Keep the function signatures stable, and replace the bodies:
- `rank_products()` → ranking / personalization service
- `get_availability()` → OMS / inventory
- `get_personalized_picks()` → segmentation / CRM

The agent stays the same. Your backends change behind the tool surface.

## Docs

- `docs/architecture.md` — how the layers fit together
- `docs/demo-script.md` — talk track for a customer call
- `docs/security-and-guardrails.md` — what we check and where

## Repo map

```
agentic-shopper-foundry-demo/
  src/
    agent.py
    server.py
    tools.py
    telemetry/
  static/
    index.html
  sample_data/
    products.json
  docs/
  requirements.txt
  run_server.py
  .env.example
```
