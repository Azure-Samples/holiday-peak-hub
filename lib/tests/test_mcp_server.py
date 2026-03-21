"""Tests for FastAPIMCPServer schema validation and metadata registration."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from holiday_peak_lib.mcp.server import FastAPIMCPServer, MCPToolSchemaRef
from pydantic import BaseModel


class EchoInput(BaseModel):
    value: str


class EchoOutput(BaseModel):
    echoed: str


@pytest.mark.asyncio
async def test_mcp_tool_valid_input_output_and_metadata() -> None:
    app = FastAPI()
    mcp = FastAPIMCPServer(app)

    async def echo_tool(payload: dict[str, object]) -> dict[str, object]:
        return {"echoed": payload["value"]}

    mcp.add_tool(
        "/echo",
        echo_tool,
        input_model=EchoInput,
        output_model=EchoOutput,
        input_schema_ref=MCPToolSchemaRef(name="EchoInput", version="v1"),
        output_schema_ref=MCPToolSchemaRef(name="EchoOutput", version="v1"),
        metadata={"owner": "test-suite"},
    )
    mcp.mount()

    client = TestClient(app)
    response = client.post("/mcp/echo", json={"value": "hello"})

    assert response.status_code == 200
    assert response.json() == {"echoed": "hello"}

    metadata = mcp.tool_metadata["/echo"]
    assert metadata["input_schema_ref"] == {"name": "EchoInput", "version": "v1"}
    assert metadata["output_schema_ref"] == {"name": "EchoOutput", "version": "v1"}
    assert metadata["metadata"]["owner"] == "test-suite"


@pytest.mark.asyncio
async def test_mcp_tool_rejects_invalid_input_payload() -> None:
    app = FastAPI()
    mcp = FastAPIMCPServer(app)

    async def echo_tool(payload: dict[str, object]) -> dict[str, object]:
        return {"echoed": payload["value"]}

    mcp.add_tool("/echo", echo_tool, input_model=EchoInput, output_model=EchoOutput)
    mcp.mount()

    client = TestClient(app)
    response = client.post("/mcp/echo", json={"missing": "value"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "invalid_tool_input"


@pytest.mark.asyncio
async def test_mcp_tool_rejects_invalid_output_payload() -> None:
    app = FastAPI()
    mcp = FastAPIMCPServer(app)

    async def bad_tool(_payload: dict[str, object]) -> dict[str, object]:
        return {"wrong": "shape"}

    mcp.add_tool("/bad", bad_tool, output_model=EchoOutput)
    mcp.mount()

    client = TestClient(app)
    response = client.post("/mcp/bad", json={})

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["error"] == "invalid_tool_output"


@pytest.mark.asyncio
async def test_mcp_tool_without_schema_models_remains_compatible() -> None:
    app = FastAPI()
    mcp = FastAPIMCPServer(app)

    async def passthrough(payload: dict[str, object]) -> dict[str, object]:
        return {"ok": True, "payload": payload}

    mcp.add_tool("/passthrough", passthrough)
    mcp.mount()

    client = TestClient(app)
    response = client.post("/mcp/passthrough", json={"a": 1})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["payload"] == {"a": 1}
    metadata = mcp.tool_metadata["/passthrough"]
    assert metadata["input_schema_ref"] is None
    assert metadata["output_schema_ref"] is None
