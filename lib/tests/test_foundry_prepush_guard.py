"""Track A3 — pre-push guard for ensure_foundry_agent.

Verifies that :func:`ensure_foundry_agent` refuses to push fallback placeholder
instructions to Foundry, and that real instructions fall through to the normal
lookup path.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from holiday_peak_lib.agents import foundry as foundry_module
from holiday_peak_lib.agents.foundry import FoundryAgentConfig, ensure_foundry_agent

_FALLBACK_INSTRUCTIONS = (
    "Structured instructions file not found for 'test-service'. "
    "This is a safety fallback — the runtime image is missing the prompt."
)

_REAL_INSTRUCTIONS = (
    "You are a catalog search assistant.\n\n"
    "Follow these guidelines when answering queries:\n"
    "- Prefer precise matches.\n"
    "- Cite product IDs when available.\n"
)


def _make_config() -> FoundryAgentConfig:
    return FoundryAgentConfig(
        endpoint="https://example-account.services.ai.azure.com/api/projects/test-project",
        agent_id="pending",
        agent_name="test-agent",
        project_name="test-project",
    )


def test_ensure_foundry_agent_refuses_fallback_instructions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback placeholder instructions must be refused before any SDK call."""

    def _fail_ensure_client(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("_ensure_client must not be called when refusing fallback")

    monkeypatch.setattr(foundry_module, "_ensure_client", _fail_ensure_client)

    config = _make_config()
    result = asyncio.run(
        ensure_foundry_agent(
            config,
            instructions=_FALLBACK_INSTRUCTIONS,
            create_if_missing=True,
        )
    )

    assert result["status"] == "fallback_instructions_refused"
    assert result["created"] is False
    assert result["error_code"] == "fallback_instructions"
    assert result["agent_id"] is None
    assert result["agent_name"] == "test-agent"
    assert "detail" in result and result["detail"]
    assert "hint" in result and result["hint"]


def test_ensure_foundry_agent_allows_real_instructions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real instructions must proceed past the guard and use the normal path."""

    class _StubAgentsClient:
        def create_version(self, *_a: Any, **_kw: Any) -> None:  # pragma: no cover
            raise AssertionError("create_version should not be called in this test")

    class _StubProjectClient:
        def __init__(self) -> None:
            self.agents = _StubAgentsClient()

        async def __aenter__(self) -> "_StubProjectClient":
            return self

        async def __aexit__(self, *_exc: Any) -> None:
            return None

    stub_client = _StubProjectClient()

    monkeypatch.setattr(foundry_module, "_ensure_client", lambda *_a, **_kw: stub_client)
    monkeypatch.setattr(
        foundry_module,
        "_close_owned_credential",
        lambda *_a, **_kw: asyncio.sleep(0),
    )

    async def _fake_lookup(*_a: Any, **_kw: Any) -> dict[str, Any]:
        return {
            "status": "exists",
            "agent_id": "agent-123",
            "agent_name": "test-agent",
            "created": False,
        }

    async def _fake_drift(*_a: Any, **_kw: Any) -> None:
        return None

    monkeypatch.setattr(foundry_module, "_lookup_existing_agent", _fake_lookup)
    monkeypatch.setattr(foundry_module, "_check_instruction_drift", _fake_drift)

    config = _make_config()
    result = asyncio.run(
        ensure_foundry_agent(
            config,
            instructions=_REAL_INSTRUCTIONS,
            create_if_missing=False,
        )
    )

    assert result["status"] == "exists"
    assert result["agent_id"] == "agent-123"
    assert result["agent_name"] == "test-agent"
