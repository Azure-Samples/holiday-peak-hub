"""Compatibility shim for opentelemetry-semantic-conventions-ai >= 0.4.14.

Version 0.4.14 removed the ``LLM_*`` attribute constants from
``opentelemetry.semconv_ai.SpanAttributes`` that ``agent-framework``
relies on.  This module patches them back **before** ``agent_framework``
is imported so that the framework can load without error.

The attribute *values* (`gen_ai.*`) are the official OpenTelemetry GenAI
convention names – only the Python constant names changed.
"""

_LEGACY_LLM_ATTRS: dict[str, str] = {
    "LLM_SYSTEM": "gen_ai.system",
    "LLM_REQUEST_MODEL": "gen_ai.request.model",
    "LLM_RESPONSE_MODEL": "gen_ai.response.model",
    "LLM_REQUEST_MAX_TOKENS": "gen_ai.request.max_tokens",
    "LLM_REQUEST_TEMPERATURE": "gen_ai.request.temperature",
    "LLM_REQUEST_TOP_P": "gen_ai.request.top_p",
    "LLM_TOKEN_TYPE": "gen_ai.token.type",
}


def patch_span_attributes() -> None:
    """Add missing ``LLM_*`` constants to ``SpanAttributes`` if absent."""
    try:
        from opentelemetry.semconv_ai import (  # type: ignore[import-untyped]
            SpanAttributes,
        )
    except ImportError:
        return  # Package not installed – nothing to patch.

    for attr_name, attr_value in _LEGACY_LLM_ATTRS.items():
        if not hasattr(SpanAttributes, attr_name):
            setattr(SpanAttributes, attr_name, attr_value)
