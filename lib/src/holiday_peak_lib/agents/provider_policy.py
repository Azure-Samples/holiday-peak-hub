"""Provider-specific runtime policy strategies for agent invocation."""

from abc import ABC, abstractmethod
from typing import Any


def normalize_messages(messages: Any) -> list[dict[str, Any]]:
    """Normalize inbound messages into a list of role/content dictionaries."""

    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    if isinstance(messages, dict):
        return [messages]
    return list(messages or [])


class ProviderPolicyStrategy(ABC):
    """Strategy interface for provider-specific invocation policies."""

    @abstractmethod
    def sanitize_messages(self, messages: Any, *, enforce_prompt_governance: bool) -> Any:
        """Return provider-compliant messages for model invocation."""

    @abstractmethod
    def should_use_local_routing_prompt(self, *, enforce_prompt_governance: bool) -> bool:
        """Return whether local routing prompts should be injected."""


class DefaultProviderPolicyStrategy(ProviderPolicyStrategy):
    """Default provider strategy: pass-through behavior."""

    def sanitize_messages(self, messages: Any, *, enforce_prompt_governance: bool) -> Any:
        return messages

    def should_use_local_routing_prompt(self, *, enforce_prompt_governance: bool) -> bool:
        return True


class FoundryProviderPolicyStrategy(ProviderPolicyStrategy):
    """Foundry strategy enforcing portal/SDK-owned prompt governance."""

    def sanitize_messages(self, messages: Any, *, enforce_prompt_governance: bool) -> Any:
        if not enforce_prompt_governance:
            return messages

        allowed_roles = {"user", "assistant"}
        normalized = normalize_messages(messages)
        sanitized: list[dict[str, Any]] = []
        for message in normalized:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "")).lower()
            if role in allowed_roles:
                sanitized.append(message)

        return sanitized or [{"role": "user", "content": str(messages)}]

    def should_use_local_routing_prompt(self, *, enforce_prompt_governance: bool) -> bool:
        return not enforce_prompt_governance


_STRATEGY_REGISTRY: dict[str, ProviderPolicyStrategy] = {
    "default": DefaultProviderPolicyStrategy(),
    "foundry": FoundryProviderPolicyStrategy(),
}


def resolve_provider_policy(provider: str | None) -> ProviderPolicyStrategy:
    """Resolve strategy by provider name with default fallback."""

    key = (provider or "default").lower()
    return _STRATEGY_REGISTRY.get(key, _STRATEGY_REGISTRY["default"])


def sanitize_messages_for_provider(
    messages: Any,
    *,
    provider: str | None,
    enforce_prompt_governance: bool,
) -> Any:
    """Convenience facade for strategy-based message sanitization."""

    strategy = resolve_provider_policy(provider)
    return strategy.sanitize_messages(
        messages,
        enforce_prompt_governance=enforce_prompt_governance,
    )


def should_use_local_routing_prompt(
    *,
    provider: str | None,
    enforce_prompt_governance: bool,
) -> bool:
    """Convenience facade for strategy-based routing prompt behavior."""

    strategy = resolve_provider_policy(provider)
    return strategy.should_use_local_routing_prompt(
        enforce_prompt_governance=enforce_prompt_governance,
    )
