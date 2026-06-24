"""Tests for the asb-v1 setup contract adapter (:mod:`agent_setup`) and its seams.

Covers the pure contract functions (resolve / apply / normalize) and the two
runtime seams wired into :meth:`BaseRetailAgent.invoke_model`:

* **setup-in** -- ``HPH_*`` env (and per-request ``_setup_override``) inject the
  model-call coordinates ``L`` (``max_output_tokens``) and ``E``
  (``reasoning_effort``) into the invoker kwargs.
* **usage-out** -- emitted model usage is normalized to the
  ``prompt_tokens`` / ``completion_tokens`` / ``total_tokens`` shape and surfaced
  under ``_telemetry.usage`` for the optimizer's token cost axis.

Backward compatibility (no env, no override) is asserted explicitly: kwargs are
untouched and no ``usage`` block is emitted when the model returns none.
"""

import pytest
from holiday_peak_lib.agents.agent_setup import (
    AgentSetup,
    apply_invocation_overrides,
    normalize_usage,
    resolve_agent_setup,
)
from holiday_peak_lib.agents.base_agent import (
    AgentDependencies,
    BaseRetailAgent,
    ModelTarget,
)

_ALL_ENV_KEYS = (
    "HPH_MAX_AGENT_STEPS",
    "HPH_MEMORY_WINDOW_TURNS",
    "HPH_TOOL_BREADTH_TIER",
    "HPH_MAX_OUTPUT_TOKENS",
    "HPH_ORCHESTRATION_MODE",
    "HPH_REASONING_EFFORT",
)


@pytest.fixture(autouse=True)
def clear_hph_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test hermetic from ambient ``HPH_*`` configuration."""
    for key in _ALL_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


# --------------------------------------------------------------------------- #
# resolve_agent_setup
# --------------------------------------------------------------------------- #
class TestResolveAgentSetup:
    """Env + override resolution for the six asb-v1 coordinates."""

    def test_no_env_no_override_is_all_none(self) -> None:
        setup = resolve_agent_setup()
        assert setup == AgentSetup()
        assert setup.to_metadata() == {}

    def test_full_env_parses_every_coordinate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HPH_MAX_AGENT_STEPS", "8")
        monkeypatch.setenv("HPH_MEMORY_WINDOW_TURNS", "4")
        monkeypatch.setenv("HPH_TOOL_BREADTH_TIER", "full")
        monkeypatch.setenv("HPH_MAX_OUTPUT_TOKENS", "2048")
        monkeypatch.setenv("HPH_ORCHESTRATION_MODE", "router_specialists")
        monkeypatch.setenv("HPH_REASONING_EFFORT", "high")

        setup = resolve_agent_setup()

        assert setup == AgentSetup(
            max_agent_steps=8,
            memory_window_turns=4,
            tool_breadth_tier="full",
            max_output_tokens=2048,
            orchestration_mode="router_specialists",
            reasoning_effort="high",
        )

    def test_invalid_values_are_dropped_not_raised(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HPH_MAX_AGENT_STEPS", "not-an-int")
        monkeypatch.setenv("HPH_MAX_OUTPUT_TOKENS", "-5")
        monkeypatch.setenv("HPH_TOOL_BREADTH_TIER", "bogus")
        monkeypatch.setenv("HPH_ORCHESTRATION_MODE", "swarm")
        monkeypatch.setenv("HPH_REASONING_EFFORT", "ULTRA")

        setup = resolve_agent_setup()

        assert setup == AgentSetup()

    def test_choice_values_are_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HPH_REASONING_EFFORT", "High")
        monkeypatch.setenv("HPH_TOOL_BREADTH_TIER", "  Minimal ")
        setup = resolve_agent_setup()
        assert setup.reasoning_effort == "high"
        assert setup.tool_breadth_tier == "minimal"

    def test_override_shadows_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HPH_MAX_OUTPUT_TOKENS", "512")
        setup = resolve_agent_setup({"max_output_tokens": 4096})
        assert setup.max_output_tokens == 4096

    def test_override_none_falls_back_to_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HPH_MAX_OUTPUT_TOKENS", "512")
        setup = resolve_agent_setup({"max_output_tokens": None})
        assert setup.max_output_tokens == 512

    def test_override_only_no_env(self) -> None:
        setup = resolve_agent_setup({"reasoning_effort": "low", "max_output_tokens": 1024})
        assert setup.reasoning_effort == "low"
        assert setup.max_output_tokens == 1024
        assert setup.tool_breadth_tier is None

    def test_non_dict_override_is_ignored(self) -> None:
        assert resolve_agent_setup("not-a-dict") == AgentSetup()  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# apply_invocation_overrides
# --------------------------------------------------------------------------- #
class TestApplyInvocationOverrides:
    """Injection of the model-call-honored coordinates into invoker kwargs."""

    def test_injects_length_and_effort(self) -> None:
        kwargs: dict = {}
        apply_invocation_overrides(
            AgentSetup(max_output_tokens=1024, reasoning_effort="medium"), kwargs
        )
        assert kwargs == {"max_output_tokens": 1024, "reasoning_effort": "medium"}

    def test_caller_value_wins_over_setup(self) -> None:
        kwargs: dict = {"max_output_tokens": 999}
        apply_invocation_overrides(
            AgentSetup(max_output_tokens=1024, reasoning_effort="low"), kwargs
        )
        assert kwargs["max_output_tokens"] == 999
        assert kwargs["reasoning_effort"] == "low"

    def test_empty_setup_is_noop(self) -> None:
        kwargs: dict = {}
        apply_invocation_overrides(AgentSetup(), kwargs)
        assert kwargs == {}


# --------------------------------------------------------------------------- #
# normalize_usage
# --------------------------------------------------------------------------- #
class TestNormalizeUsage:
    """Usage shape adaptation for the optimizer's token cost axis."""

    def test_agent_framework_shape_is_remapped(self) -> None:
        result = normalize_usage(
            {
                "input_token_count": 12,
                "output_token_count": 8,
                "total_token_count": 20,
            }
        )
        assert result == {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
        }

    def test_openai_shape_passes_through(self) -> None:
        result = normalize_usage({"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8})
        assert result == {
            "prompt_tokens": 5,
            "completion_tokens": 3,
            "total_tokens": 8,
        }

    def test_total_is_derived_when_absent(self) -> None:
        result = normalize_usage({"input_token_count": 5, "output_token_count": 7})
        assert result == {
            "prompt_tokens": 5,
            "completion_tokens": 7,
            "total_tokens": 12,
        }

    def test_partial_usage_keeps_only_present_keys(self) -> None:
        assert normalize_usage({"input_token_count": 5}) == {
            "prompt_tokens": 5,
            "total_tokens": 5,
        }

    def test_zero_total_is_preserved(self) -> None:
        assert normalize_usage({"total_tokens": 0}) == {"total_tokens": 0}

    def test_booleans_are_rejected(self) -> None:
        assert normalize_usage({"prompt_tokens": True}) is None

    @pytest.mark.parametrize("raw", [None, {}, "string", [1, 2], 42])
    def test_unusable_input_returns_none(self, raw: object) -> None:
        assert normalize_usage(raw) is None


# --------------------------------------------------------------------------- #
# End-to-end seams through BaseRetailAgent.invoke_model
# --------------------------------------------------------------------------- #
class _SetupProbeAgent(BaseRetailAgent):
    """Minimal agent used to observe the invoke_model seams."""

    async def handle(self, request: dict) -> dict:  # pragma: no cover - unused
        return {"status": "ok", "request": request}


def _make_capturing_agent(captured: dict, *, usage: dict | None) -> _SetupProbeAgent:
    """Build an agent whose single SLM invoker records kwargs and emits ``usage``."""

    async def invoker(**kwargs: object) -> dict:
        captured.clear()
        captured.update(kwargs)
        response: dict = {"content": "ok", "response": "ok"}
        if usage is not None:
            response["usage"] = usage
        return response

    slm = ModelTarget(
        name="probe-slm",
        model="gpt-5-nano",
        invoker=invoker,
        temperature=0.2,
        top_p=0.9,
    )
    return _SetupProbeAgent(config=AgentDependencies(slm=slm, llm=None))


class TestInvokeModelSeams:
    """Seam (a) usage threading and seam (b) L/E injection, end to end."""

    @pytest.mark.asyncio
    async def test_env_injects_length_and_effort_and_normalizes_usage(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HPH_MAX_OUTPUT_TOKENS", "1024")
        monkeypatch.setenv("HPH_REASONING_EFFORT", "high")
        captured: dict = {}
        agent = _make_capturing_agent(
            captured,
            usage={
                "input_token_count": 30,
                "output_token_count": 12,
                "total_token_count": 42,
            },
        )

        result = await agent.invoke_model(
            {"query": "hello"}, [{"role": "user", "content": "hello"}]
        )

        # Seam (b): swept length + effort reached the invoker.
        assert captured["max_output_tokens"] == 1024
        assert captured["reasoning_effort"] == "high"
        # Seam (a): emitted usage normalized onto _telemetry.usage.
        assert result["_telemetry"]["usage"] == {
            "prompt_tokens": 30,
            "completion_tokens": 12,
            "total_tokens": 42,
        }

    @pytest.mark.asyncio
    async def test_request_override_injects_without_env(self) -> None:
        captured: dict = {}
        agent = _make_capturing_agent(captured, usage=None)

        await agent.invoke_model(
            {
                "query": "hello",
                "_setup_override": {
                    "max_output_tokens": 2048,
                    "reasoning_effort": "low",
                },
            },
            [{"role": "user", "content": "hello"}],
        )

        assert captured["max_output_tokens"] == 2048
        assert captured["reasoning_effort"] == "low"

    @pytest.mark.asyncio
    async def test_no_env_no_override_is_backward_compatible(self) -> None:
        captured: dict = {}
        agent = _make_capturing_agent(captured, usage=None)

        result = await agent.invoke_model(
            {"query": "hello"}, [{"role": "user", "content": "hello"}]
        )

        # No swept coordinates leak into the invoker kwargs.
        assert "max_output_tokens" not in captured
        assert "reasoning_effort" not in captured
        # No usage emitted by the model -> no usage block synthesized.
        assert "usage" not in result["_telemetry"]
