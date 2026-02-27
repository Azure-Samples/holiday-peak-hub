"""Agent builders and runtime primitives."""

# Patch missing LLM_* attrs on SpanAttributes before agent_framework loads.
from ._otel_compat import patch_span_attributes as _patch_span_attributes

_patch_span_attributes()
del _patch_span_attributes

from .base_agent import AgentDependencies, BaseRetailAgent, ModelTarget
from .builder import AgentBuilder
from .foundry import (
    FoundryAgentConfig,
    build_foundry_model_target,
    ensure_foundry_agent,
)

__all__ = [
    "AgentBuilder",
    "AgentDependencies",
    "BaseRetailAgent",
    "ModelTarget",
    "FoundryAgentConfig",
    "build_foundry_model_target",
    "ensure_foundry_agent",
]
