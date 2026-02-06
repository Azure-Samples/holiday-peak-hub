from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import runtime
from .telemetry.trace import add_event, end_trace, start_trace
from .tools import _load_products


class ChatRequest(BaseModel):
    message: str
    # UI context (PDP/PLP style)
    product_id: Optional[str] = None
    category: Optional[str] = None
    user_segment: Optional[str] = None
    # Demo mode toggles
    show_debug: bool = True


class ChatResponse(BaseModel):
    text: str
    trace: Optional[list[dict]] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()


app = FastAPI(title="Agentic Shopper (Foundry + Agent Framework)", lifespan=lifespan)

static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return (static_dir / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {"ok": True}


@app.get("/api/catalog")
async def catalog(category: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    products = _load_products()
    if category:
        products = [p for p in products if p.get("category") == category]
    return {"items": products}


@app.get("/api/product/{sku}")
async def product_detail(sku: str) -> Dict[str, Any]:
    for p in _load_products():
        if p.get("sku") == sku:
            return p
    return {"error": "not_found", "sku": sku}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> Dict[str, Any]:
    start_trace()
    add_event(
        "request",
        "Incoming chat",
        {
            "message": req.message,
            "product_id": req.product_id,
            "category": req.category,
            "user_segment": req.user_segment,
        },
    )

    # Guardrail example: keep V1 scoped (and explain it in the trace)
    add_event("guardrail", "Scope check", {"v1_checkout": False, "v1_returns": False})

    # Minimal context capsule (PDP/PLP style). In production this is derived from page context + profile.
    preamble_parts = []
    if req.product_id:
        preamble_parts.append(f"ProductID: {req.product_id}")
    if req.category:
        preamble_parts.append(f"Category: {req.category}")
    if req.user_segment:
        preamble_parts.append(f"UserSegment: {req.user_segment}")

    message = req.message
    if preamble_parts:
        message = "\n".join(["Context:", *preamble_parts, "", "User:", req.message])
        add_event("context", "Injected page/user context", {"context_lines": preamble_parts})

    add_event("agent", "Running agent")

    result = await runtime.run(message)

    # Ensure we return a real string (not AgentThread or other object)
    result_text = result if isinstance(result, str) else str(result)

    add_event("agent", "Agent completed")

    trace = end_trace() if req.show_debug else None

    # Ensure trace is JSON-safe too
    safe_trace = jsonable_encoder(trace) if trace is not None else None

    return {"text": result_text, "trace": safe_trace}
