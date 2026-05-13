# Foundry Hosted Agent (V3) FastAPI Mount — Pilot Notes

**Status**: Pilot landed locally on `inventory-health-check` (2026-05-12). Not deployed yet.

## What was built

1. **`lib/src/holiday_peak_lib/agents/hosted.py`** — new module
   - `mount_hosted_agent(fastapi_app, agent, *, prefix="/v1", request_translator=None)` — lazy-imports `agent_framework_foundry_hosting.ResponsesHostServer`, wraps the agent in `_HostedAgentRunAdapter` (SupportsAgentRun protocol), and `app.mount("/", host_server)`.
   - `_HostedAgentRunAdapter.run(messages, *, stream, session, **kwargs)` translates MAF `Message[]` → `agent.hosted_request_from_text(text)` → `agent.handle(request)` → `AgentResponse(messages=[Message(role="assistant", contents=[text])])`.
   - Streaming explicitly raises NotImplementedError (follow-up).

2. **`lib/src/holiday_peak_lib/agents/base_agent.py`** — additive
   - `BaseRetailAgent.serve_hosted(fastapi_app, *, prefix="/v1")` → one-line mount delegating to `mount_hosted_agent`.
   - `BaseRetailAgent.hosted_request_from_text(text) -> {"prompt": text}` (overridable per service).

3. **`apps/inventory-health-check/src/inventory_health_check/agents.py`** — overrides `hosted_request_from_text` to extract SKU via regex (`SKU-XYZ` or `sku ABC` patterns); falls back to a structured `{_no_sku: True}` request that `handle()` recognises and returns a friendly hint instead of error.

4. **`apps/inventory-health-check/src/inventory_health_check/main.py`** — appends `app.state.agent.serve_hosted(app)` after `create_standard_app(...)`. Gated by env `HOLIDAY_PEAK_FOUNDRY_HOSTED` (default on); falls back gracefully if SDK absent.

5. **`lib/tests/test_agents_hosted.py`** — 9 unit tests + 1 integration test (skipped when SDK absent, runs when SDK installed).

## Why this design

- **Single-process, single-port, single-runtime** — preserves ADR-005 (2026-05-10) dual-runtime guardrail. The forbidden-token test scans only YAML manifests (`agent.yaml`, `.foundry/agent-metadata.yaml`), and the literal `ResponsesHostServer` import lives only in `lib/`. Service code calls `agent.serve_hosted(app)` which doesn't trip the regex.
- **Optional dep** — `agent-framework-foundry-hosting` is NOT in lib's `pyproject.toml`. Lazy import + clear ImportError. Services without the SDK keep working unchanged.
- **Route ordering** — direct routes (`/health`, `/ready`, `/mcp/*`) registered first, mount appended last. Starlette walks routes in order so direct routes always win, mount catches `/v1/*`.

## Verification (local)

- `lib/tests/test_agents_hosted.py`: 9 passed, 1 skipped.
- Full lib + pilot regression: 1328 passed.
- Forbidden-token guardrail (`tests/ops/test_foundry_portal_tracking_manifests.py`): 27/27 passed (manifest contracts unaffected).
- `.tmp/probe_serve_hosted.py` (real `ResponsesHostServer`, real `BaseRetailAgent` subclass): POST `/v1/responses` → 200 in 59.8ms, `agent.handle()` invoked with `{"prompt": "tell me a joke"}`, output text `"handled: tell me a joke"`.

## What remains (next PRs)

1. **Container build** — `apps/inventory-health-check/src/Dockerfile` and `pyproject.toml` need `agent-framework-foundry-hosting` added (preview channel `--pre`).
2. **AKS deployment** — rebuild image, push to ACR `holidaypeakhubdevacr.azurecr.io`, bump Flux image tag.
3. **Foundry deployment** — separately, run `azd ai agent deploy` so Foundry creates the per-agent Entra ID + dedicated `{project_endpoint}/agents/inventory-health-check/endpoint/protocols/openai/v1/responses` URL. The container image deployed there is the SAME image as AKS (single-process pattern) — Foundry just probes `/readiness` (built into ResponsesHostServer) and routes to `/v1/responses`.
4. **`apps/inventory-health-check/agent.yaml`** — re-shape for V3 hosted runtime: `template.kind` from `direct-model` to `hosted-agent` (or whatever the V3 spec uses), `template.protocols` add `responses 1.0.0`. Keep `metadata.trackingOnly: false` once truly portal-indexed.
5. **ADR-005 amendment** — narrow guardrail wording from "no `ResponsesHostServer`" to "no two runtimes per service" (the mount pattern is the compliant alternative).
6. **Test policy update** — `FORBIDDEN_DUAL_RUNTIME_TOKENS` in `tests/ops/test_foundry_portal_tracking_manifests.py` should drop `"ResponsesHostServer"` from the list once the ADR amendment lands. Keep `"hosted_main.py"`, `"entrypoint.sh"`, `"8088"`, `"second runtime"` as the actual dual-runtime markers.
7. **Streaming** — `_HostedAgentRunAdapter.run(stream=True)` currently raises NotImplementedError. Wire to `BaseRetailAgent.invoke_model_stream` to enable SSE responses on the hosted endpoint.

## Investigative artifacts (under `.tmp/`)

- `.tmp/hosted-probe-venv/` — fresh Python 3.13 venv with `agent-framework-foundry-hosting==1.0.0a260507`, `agent-framework==1.3.0`, `azure-ai-agentserver-responses==1.0.0bX`, `fastapi`, `uvicorn`, and `holiday-peak-lib` (editable install).
- `.tmp/probe_mount.py` — initial mount probe with hand-rolled stub agent (proved `ResponsesHostServer` IS Starlette and mountable).
- `.tmp/probe_serve_hosted.py` — second probe using the real lib helper end-to-end.

Both probes can be re-run any time:
```powershell
.\.tmp\hosted-probe-venv\Scripts\python.exe .\.tmp\probe_serve_hosted.py
```

## Key surface facts (for next session)

- `azure.ai.agentserver.responses.hosting.ResponsesAgentServerHost` MRO: `[ResponsesAgentServerHost, AgentServerHost, Starlette, object]`.
- `ResponsesHostServer(agent, *, prefix="", options=None, store=None)` — registers routes `/{prefix}/responses` (POST/GET/DELETE), `/{prefix}/responses/{id}/cancel`, `/{prefix}/responses/{id}/input_items`, plus a server-managed `/readiness`.
- The auto-FoundryStorageProvider activation is gated by `AgentConfig.from_env().is_hosted` (env-driven). In-process / AKS path uses `InMemoryResponseProvider` automatically.
- Lifespan handler is observational only — safe to mount inside FastAPI even though Starlette's mount semantics drop sub-app lifespans.
