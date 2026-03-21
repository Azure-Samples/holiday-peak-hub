"""Thin wrapper to expose MCP endpoints over FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, ValidationError

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]]


@dataclass(frozen=True, slots=True)
class MCPToolSchemaRef:
    """Versioned schema reference for MCP tool contracts."""

    name: str
    version: str
    uri: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name, "version": self.version}
        if self.uri:
            payload["uri"] = self.uri
        return payload


class FastAPIMCPServer:
    """Registers MCP routes on a FastAPI app."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.router = APIRouter()
        self._tool_metadata: dict[str, dict[str, Any]] = {}

    @property
    def tool_metadata(self) -> dict[str, dict[str, Any]]:
        """Return metadata registered for each MCP tool path."""
        return dict(self._tool_metadata)

    def add_tool(
        self,
        path: str,
        handler: ToolHandler,
        *,
        input_model: type[BaseModel] | None = None,
        output_model: type[BaseModel] | None = None,
        input_schema_ref: MCPToolSchemaRef | None = None,
        output_schema_ref: MCPToolSchemaRef | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        normalized_path = self._normalize_path(path)
        validated_handler = self._wrap_handler(handler, input_model, output_model)
        self.router.post(normalized_path)(validated_handler)
        self._tool_metadata[normalized_path] = {
            "input_schema_ref": self._resolve_schema_ref(input_schema_ref, input_model),
            "output_schema_ref": self._resolve_schema_ref(output_schema_ref, output_model),
            "metadata": dict(metadata or {}),
        }

    def mount(self) -> None:
        self.app.include_router(self.router, prefix="/mcp")

    def _normalize_path(self, path: str) -> str:
        if not path.startswith("/"):
            return f"/{path}"
        return path

    def _resolve_schema_ref(
        self,
        schema_ref: MCPToolSchemaRef | None,
        model: type[BaseModel] | None,
    ) -> dict[str, Any] | None:
        if schema_ref is not None:
            return schema_ref.to_dict()
        if model is None:
            return None
        return MCPToolSchemaRef(name=model.__name__, version="v1").to_dict()

    def _wrap_handler(
        self,
        handler: ToolHandler,
        input_model: type[BaseModel] | None,
        output_model: type[BaseModel] | None,
    ) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
        async def validated_handler(payload: dict[str, Any]) -> dict[str, Any]:
            normalized_payload = payload
            if input_model is not None:
                try:
                    validated_input = input_model.model_validate(payload)
                except ValidationError as exc:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "error": "invalid_tool_input",
                            "issues": exc.errors(),
                        },
                    ) from exc
                normalized_payload = validated_input.model_dump(mode="json")

            result = handler(normalized_payload)
            if isawaitable(result):
                result = await result

            if output_model is not None:
                try:
                    validated_output = output_model.model_validate(result)
                except ValidationError as exc:
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": "invalid_tool_output",
                            "issues": exc.errors(),
                        },
                    ) from exc
                return validated_output.model_dump(mode="json")

            if isinstance(result, BaseModel):
                return result.model_dump(mode="json")
            if not isinstance(result, dict):
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "invalid_tool_output",
                        "issues": [
                            {
                                "message": "Tool handlers must return a dict payload",
                                "type": "type_error.dict",
                            }
                        ],
                    },
                )
            return result

        return validated_handler
