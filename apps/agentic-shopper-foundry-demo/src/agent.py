import asyncio
from typing import Optional, List, Any

from azure.identity.aio import AzureCliCredential, DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential

from agent_framework import ChatAgent

from agent_framework_azure_ai import AzureAIClient
from agent_framework_azure_ai_search import AzureAISearchContextProvider

from .config import Settings
from .tools import get_availability, get_personalized_picks, rank_products


SHOPPER_INSTRUCTIONS = """
You are an agentic shopping assistant for an outdoor apparel brand.

V1 responsibilities:
- Read product facts from provided context (RAG) when available
- Recommend 1–3 products with clear tradeoffs
- Explain your recommendation in plain language
- Use tools for ranking, availability, and personalization
- Ask at most ONE clarifying question if key info is missing

Out of scope for V1:
- Checkout / payments
- Dynamic pricing
- Inventory rebalancing
- Order changes / returns

Output format:
- Short answer first
- Then a bulleted 'Why' section
- Then 'Top picks' (1–3) with: SKU, who it's for, key specs
""".strip()


def _stringify_content(content: Any) -> str:
    """Best-effort conversion of message content to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content

    # Sometimes content is a list of parts (text, image, etc.)
    if isinstance(content, list):
        parts: list[str] = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                # common shapes: {"type":"text","text":"..."} or {"text":"..."}
                if "text" in p and isinstance(p["text"], str):
                    parts.append(p["text"])
                elif "content" in p and isinstance(p["content"], str):
                    parts.append(p["content"])
            else:
                # fallback
                parts.append(str(p))
        return "\n".join([x for x in parts if x])

    if isinstance(content, dict):
        for k in ("text", "content", "message"):
            v = content.get(k)
            if isinstance(v, str):
                return v
        return str(content)

    return str(content)


def _extract_text(res: Any) -> str:
    """
    Normalize agent-framework results to a JSON-safe plain string.
    Handles AgentThread outputs (the cause of your serialization error).
    """
    if res is None:
        return ""

    # If agent returns (thread, something) or [thread, ...]
    if isinstance(res, (tuple, list)) and len(res) > 0:
        # Prefer the last item (often the final output), but if it's a thread, we'll handle it below.
        res = res[-1]

    # Direct string
    if isinstance(res, str):
        return res

    # AgentThread (or similar) — look for messages and grab last assistant message
    if type(res).__name__ == "AgentThread" or hasattr(res, "messages"):
        msgs = getattr(res, "messages", None)
        if msgs and isinstance(msgs, list):
            # scan backwards for assistant role
            for m in reversed(msgs):
                role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else None)
                if role == "assistant" or role == "model":
                    content = getattr(m, "content", None)
                    if content is None and isinstance(m, dict):
                        content = m.get("content") or m.get("text") or m.get("message")
                    if content is None:
                        content = getattr(m, "text", None)
                    return _stringify_content(content)

            # fallback: last message of any role
            m = msgs[-1]
            content = getattr(m, "content", None)
            if content is None and isinstance(m, dict):
                content = m.get("content") or m.get("text") or m.get("message")
            if content is None:
                content = getattr(m, "text", None)
            return _stringify_content(content)

        # If no messages list, last resort
        return str(res)

    # Common response shapes (non-thread)
    if hasattr(res, "text"):
        try:
            return str(res.text)
        except Exception:
            pass

    if isinstance(res, dict):
        for k in ("text", "message", "content", "output"):
            v = res.get(k)
            if isinstance(v, str):
                return v
        return str(res)

    # Last resort
    return str(res)


class AgentRuntime:
    def __init__(self) -> None:
        self.settings = Settings()
        self.credential = None
        self.client: Optional[AzureAIClient] = None
        self.agent: Optional[ChatAgent] = None

    async def start(self) -> None:
        self.settings.validate()

        if self.settings.AUTH_MODE == "default":
            self.credential = DefaultAzureCredential()
        else:
            self.credential = AzureCliCredential()

        self.client = AzureAIClient(
            project_endpoint=self.settings.AZURE_AI_PROJECT_ENDPOINT,
            model_deployment_name=self.settings.AZURE_AI_MODEL_DEPLOYMENT_NAME,
            credential=self.credential,
        )

        context_providers: Optional[List[AzureAISearchContextProvider]] = None
        if self.settings.AZURE_SEARCH_ENDPOINT and self.settings.AZURE_SEARCH_INDEX_NAME:
            search_cred = (
                AzureKeyCredential(self.settings.AZURE_SEARCH_API_KEY)
                if getattr(self.settings, "AZURE_SEARCH_API_KEY", None)
                else self.credential
            )

            context_providers = [
                AzureAISearchContextProvider(
                    endpoint=self.settings.AZURE_SEARCH_ENDPOINT,
                    index_name=self.settings.AZURE_SEARCH_INDEX_NAME,
                    credential=search_cred,
                    top_k=3,
                )
            ]

        # In your installed build this is required: chat_client=
        self.agent = ChatAgent(
            name="AgenticShopperV1",
            instructions=SHOPPER_INSTRUCTIONS,
            chat_client=self.client,
            tools=[rank_products, get_availability, get_personalized_picks],
            context_providers=context_providers,
        )

    async def run(self, message: str) -> str:
        if self.agent is None:
            raise RuntimeError("Agent is not initialized. Did runtime.start() run?")

        for method_name in ("run", "chat", "invoke", "respond", "complete"):
            method = getattr(self.agent, method_name, None)
            if callable(method):
                res = method(message)
                if asyncio.iscoroutine(res):
                    res = await res
                return _extract_text(res)

        raise AttributeError("ChatAgent has no supported execution method.")

    async def stop(self) -> None:
        try:
            if self.client is not None and hasattr(self.client, "close"):
                maybe = self.client.close()
                if asyncio.iscoroutine(maybe):
                    await maybe
        finally:
            if self.credential is not None:
                await self.credential.close()


runtime = AgentRuntime()
