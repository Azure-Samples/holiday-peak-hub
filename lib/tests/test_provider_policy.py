"""Tests for provider policy helpers."""

from holiday_peak_lib.agents.provider_policy import (
    sanitize_messages_for_provider,
    should_use_local_routing_prompt,
)


def test_sanitize_messages_foundry_governed():
    messages = [
        {"role": "system", "content": "local"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "ok"},
    ]
    sanitized = sanitize_messages_for_provider(
        messages,
        provider="foundry",
        enforce_prompt_governance=True,
    )
    assert sanitized == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "ok"},
    ]


def test_sanitize_messages_non_foundry_passthrough():
    messages = [{"role": "system", "content": "local"}, {"role": "user", "content": "hello"}]
    sanitized = sanitize_messages_for_provider(
        messages,
        provider="openai",
        enforce_prompt_governance=True,
    )
    assert sanitized == messages


def test_routing_prompt_disabled_for_foundry_when_governed():
    assert (
        should_use_local_routing_prompt(provider="foundry", enforce_prompt_governance=True)
        is False
    )


def test_routing_prompt_enabled_when_governance_disabled():
    assert (
        should_use_local_routing_prompt(provider="foundry", enforce_prompt_governance=False)
        is True
    )
