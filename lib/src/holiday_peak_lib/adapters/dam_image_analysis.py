"""DAM-backed image analysis adapter for product attribute enrichment."""

from __future__ import annotations

import json
import os
from typing import Any, Awaitable, Callable

from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter
from holiday_peak_lib.integrations import DAMConnectionConfig, GenericDAMConnector


def _coerce_confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


class DAMImageAnalysisAdapter(BaseAdapter):
    """Analyze DAM images with a vision-capable model and return structured output."""

    def __init__(
        self,
        *,
        dam_connector: GenericDAMConnector | Any | None = None,
        vision_invoker: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        prompt_builder: Callable[..., list[dict[str, Any]]] | None = None,
        max_images: int = 4,
    ) -> None:
        super().__init__(
            max_calls=8,
            per_seconds=1.0,
            cache_ttl=15.0,
            retries=2,
            timeout=12.0,
            circuit_breaker_threshold=5,
            circuit_reset_seconds=20.0,
        )
        self._dam_connector = dam_connector or self._build_default_dam_connector()
        self._vision_invoker = vision_invoker
        self._prompt_builder = prompt_builder
        self._max_images = max(1, max_images)

    def set_vision_invoker(
        self, vision_invoker: Callable[..., Awaitable[dict[str, Any]]] | None
    ) -> None:
        self._vision_invoker = vision_invoker

    def set_vision_prompt_builder(
        self,
        prompt_builder: Callable[..., list[dict[str, Any]]] | None,
    ) -> None:
        self._prompt_builder = prompt_builder

    async def analyze_attribute_from_images(
        self,
        *,
        entity_id: str,
        field_name: str,
        product: dict[str, Any],
        field_definition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            records = await self.fetch(
                {
                    "entity_id": entity_id,
                    "field_name": field_name,
                    "product": product,
                    "field_definition": field_definition or {},
                }
            )
            first = list(records)[0] if records else None
            return first or self._fallback("no_assets", field_name)
        except AdapterError:
            return self._fallback("adapter_failure", field_name)

    async def disconnect(self) -> None:
        await self._disconnect_impl()

    async def _connect_impl(self, **kwargs: Any) -> None:
        return None

    async def _disconnect_impl(self) -> None:
        if self._dam_connector is None:
            return
        close = getattr(self._dam_connector, "close", None)
        if close is None:
            return
        await self._dam_connector.close()

    async def _fetch_impl(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        entity_id = str(query.get("entity_id", ""))
        field_name = str(query.get("field_name", ""))
        product = query.get("product") or {}
        field_definition = query.get("field_definition") or {}

        if self._dam_connector is None:
            return [self._fallback("no_assets", field_name)]

        assets = await self._dam_connector.get_assets_by_product(entity_id)
        image_urls = self._extract_image_urls(assets)
        if not image_urls:
            return [self._fallback("no_assets", field_name)]
        if self._vision_invoker is None:
            return [self._fallback("no_foundry_invoker", field_name)]

        messages = self._build_vision_messages(
            product=product,
            field_name=field_name,
            field_definition=field_definition,
            image_urls=image_urls,
        )
        vision_raw = await self._vision_invoker(
            request={"entity_id": entity_id, "field_name": field_name, "source": "image_analysis"},
            messages=messages,
        )
        parsed = self._parse_vision_response(vision_raw)
        parsed.setdefault("metadata", {})
        parsed["metadata"] = {
            **parsed["metadata"],
            "source": "image_analysis",
            "assets_count": len(image_urls),
            "assets": image_urls,
        }
        return [parsed]

    async def _upsert_impl(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        return payload

    async def _delete_impl(self, identifier: str) -> bool:
        return True

    def _cache_key(self, query: dict[str, Any]) -> tuple:
        return (
            ("entity_id", str(query.get("entity_id", ""))),
            ("field_name", str(query.get("field_name", ""))),
        )

    def _extract_image_urls(self, assets: list[Any]) -> list[str]:
        urls: list[str] = []
        for asset in assets:
            if hasattr(asset, "url"):
                url = getattr(asset, "url")
            elif isinstance(asset, dict):
                url = asset.get("url") or asset.get("asset_url") or asset.get("cdn_url")
            else:
                url = None
            if not url:
                continue
            urls.append(str(url))
            if len(urls) >= self._max_images:
                break
        return urls

    def _build_vision_messages(
        self,
        *,
        product: dict[str, Any],
        field_name: str,
        field_definition: dict[str, Any],
        image_urls: list[str],
    ) -> list[dict[str, Any]]:
        if self._prompt_builder is not None:
            return self._prompt_builder(
                product=product,
                field_name=field_name,
                field_definition=field_definition,
                image_urls=image_urls,
            )

        field_hint = (
            f"type={field_definition.get('type', 'string')}; "
            f"description={field_definition.get('description', '')}"
        )
        text_prompt = (
            "Infer the missing product attribute from product context and provided images. "
            "Return JSON only with keys: value, confidence, evidence, metadata. "
            f"Target field: {field_name}. Hint: {field_hint}. Product: {product}"
        )
        content_parts: list[dict[str, Any]] = [{"type": "text", "text": text_prompt}]
        content_parts.extend(
            {"type": "image_url", "image_url": {"url": image_url}} for image_url in image_urls
        )
        return [
            {
                "role": "system",
                "content": "You are a vision enrichment assistant for product catalog data.",
            },
            {"role": "user", "content": content_parts},
        ]

    def _parse_vision_response(self, raw: Any) -> dict[str, Any]:
        payload = raw
        if isinstance(raw, str):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = None

        if isinstance(payload, dict) and "value" in payload:
            return {
                "value": payload.get("value"),
                "confidence": _coerce_confidence(payload.get("confidence", 0.0)),
                "evidence": str(payload.get("evidence", "image analysis")),
                "metadata": (
                    payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
                ),
            }
        return {
            "value": None,
            "confidence": 0.0,
            "evidence": "vision response unavailable",
            "metadata": {"source": "image_analysis", "fallback_reason": "invalid_vision_response"},
        }

    def _fallback(self, reason: str, field_name: str) -> dict[str, Any]:
        return {
            "value": None,
            "confidence": 0.0,
            "evidence": f"image analysis unavailable for {field_name}",
            "metadata": {"source": "image_analysis", "fallback_reason": reason},
        }

    def _build_default_dam_connector(self) -> GenericDAMConnector | None:
        endpoint = os.getenv("DAM_ENDPOINT") or os.getenv("DAM_BASE_URL")
        api_key = os.getenv("DAM_API_KEY")
        if not endpoint:
            return None

        config = DAMConnectionConfig(
            base_url=endpoint,
            auth_type="api_key" if api_key else "bearer",
            auth_credentials=(
                {"header": "X-Api-Key", "key": api_key or ""} if api_key else {"token": ""}
            ),
        )
        return GenericDAMConnector(config)


__all__ = ["DAMImageAnalysisAdapter"]
