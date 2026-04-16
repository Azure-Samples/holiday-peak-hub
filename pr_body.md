## Summary

Combined feature PR delivering streaming-first agent architecture, GPT-5 model configurations, truth agent prompt engineering, APIM synchronization, demo pipeline tooling, and lean Docker images across all 28 services.

### Changes

**Agent Framework (lib)**
- Streaming-first agent architecture with session persistence
- GPT-5 model configurations at max capacity (SLM/LLM routing)
- Telemetry mixin and registration helpers for agents
- Complexity evaluator for SLM-first routing decisions
- SOLID, performance, and DRY refactoring across base agent and foundry

**Infrastructure**
- Bicep: streaming env vars for all 27 Container Apps
- APIM sync hook (sync-apim-agents.ps1) for automated API gateway updates
- Lean Docker images: pre-built .whl + requirements.txt (smaller, faster builds)
- Helm values update for new streaming config

**Truth Agents**
- Instruction prompts for truth-enrichment, truth-export, truth-hitl, truth-ingestion, search-enrichment-agent
- Enrichment adapter refactoring with improved error handling

**UI (Next.js)**
- Enrichment monitor admin page with CSV upload panel and live processing log
- Session persistence via PageSessionProvider
- Streaming search service and hook (useStreamingSearch)
- ChatWidget streaming support improvements

**Demo Pipeline**
- Full demo scripts: export_products_csv.py, upload_and_trigger.py, validate_search.py
- PowerShell orchestrators: run_full_demo.ps1, deploy_demo_services.ps1
- Sample data: products_export.csv/json (110 products)
- Comprehensive test coverage for all demo scripts

**Dependencies**
- fastapi 0.135.3, uvicorn 0.44.0, azure-ai-projects 2.0.1, redis 7.4.0
- UI deps bump + debug launch configs
- Next.js 16 tsconfig fix

### Testing
- 1186 lib tests passed
- 662 app tests passed
- All pre-push lint gates passed (isort, black, pylint 9.91/10, mypy, markdown links, event schema contracts)
