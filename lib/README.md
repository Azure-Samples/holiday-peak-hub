# Holiday Peak Lib

Core micro-framework for retail agent services. Provides adapters, agents with builder pattern, MCP + FastAPI integration, and multi-tier memory (Redis hot, Cosmos warm, Blob cold).

## Usage

```bash
pip install -e .[dev]
```

Then build an agent:

```python
from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent
from holiday_peak_lib.agents.memory import hot, warm, cold
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from fastapi import FastAPI

class DemoAgent(BaseRetailAgent):
    async def handle(self, request):
        return {"echo": request}

app = FastAPI()
mcp = FastAPIMCPServer(app)
agent = (
    AgentBuilder()
    .with_agent(DemoAgent)
    .with_memory(hot.HotMemory("redis://localhost:6379"), warm.WarmMemory("https://cosmos", "db", "container"), cold.ColdMemory("https://storage", "container"))
    .with_mcp(mcp)
    .build()
)
```

## Extension Points
- Implement custom adapters by subclassing `BaseAdapter`.
- Register tools via `AgentBuilder.with_tool`.
- Swap memory providers by implementing the same interface as `HotMemory`, `WarmMemory`, `ColdMemory`.
