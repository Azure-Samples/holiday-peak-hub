# Testing Guardrails

- E2E testing in this repo is **skill-driven** via `.github/skills/agent-e2e-validation/` — live APIM endpoint calls, not pytest
- NEVER create pytest files under `tests/e2e/` at the repo root — this was done once by mistake (hallucinated mocked tests), caught and deleted
- If Foundry/APIM/agents are mocked, it's an integration test, not e2e — place in `apps/*/tests/integration/`
- Always check `.github/skills/` before creating any new test category
- App-scoped e2e (e.g., `apps/crud-service/tests/e2e/`) is OK when testing the app's own HTTP surface
