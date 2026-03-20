"""Enrichment engine: AI-powered field generation and confidence scoring."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

AUTO_APPROVE_THRESHOLD_DEFAULT = 0.95


class EnrichmentEngine:
    """Generate proposed attribute values using AI and score confidence."""

    def __init__(self, auto_approve_threshold: float = AUTO_APPROVE_THRESHOLD_DEFAULT) -> None:
        self.auto_approve_threshold = auto_approve_threshold

    def build_prompt(
        self,
        product: dict[str, Any],
        field_name: str,
        field_definition: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, str]]:
        """Build a prompt for the AI model to generate a missing field value."""
        field_hint = ""
        if field_definition:
            field_hint = (
                f" Field type: {field_definition.get('type', 'string')}."
                f" Description: {field_definition.get('description', '')}."
            )
        system_msg = (
            "You are a product data enrichment assistant. "
            "Given a product record and a missing field, generate an accurate and concise value. "
            "Respond ONLY with a JSON object: "
            '{"value": <proposed value>, "confidence": <float 0.0-1.0>, "evidence": <brief rationale>}.'
        )
        user_msg = {
            "product": product,
            "missing_field": field_name,
            "field_definition": field_definition or {},
            "instruction": (
                f"Generate a value for the '{field_name}' field.{field_hint} "
                "Be concise and factual. Only use information present in the product record."
            ),
        }
        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": str(user_msg)},
        ]

    def build_vision_prompt(
        self,
        *,
        product: dict[str, Any],
        field_name: str | None = None,
        field_definition: Optional[dict[str, Any]] = None,
        image_urls: list[str] | None = None,
        image_url: str | None = None,
        missing_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Build a Foundry vision prompt using text + image_url content parts."""
        target_field = field_name or (missing_fields[0] if missing_fields else "unknown_field")
        resolved_image_urls = list(image_urls or [])
        if image_url:
            resolved_image_urls.append(image_url)

        field_hint = ""
        if field_definition:
            field_hint = (
                f" Field type: {field_definition.get('type', 'string')}."
                f" Description: {field_definition.get('description', '')}."
            )

        instruction = (
            "Infer the missing attribute from product context and images. "
            f"Target field: {target_field}.{field_hint} "
            "Return ONLY JSON with keys: value, confidence, evidence, metadata."
        )
        content_parts: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": str(
                    {
                        "instruction": instruction,
                        "missing_field": target_field,
                        "product": product,
                    }
                ),
            }
        ]
        content_parts.extend(
            {"type": "image_url", "image_url": {"url": url}} for url in resolved_image_urls
        )

        return [
            {
                "role": "system",
                "content": "You are a vision enrichment assistant for product catalog data.",
            },
            {"role": "user", "content": content_parts},
        ]

    def parse_ai_response(self, raw: Any) -> dict[str, Any]:
        """Parse AI response into structured proposed attribute fields."""
        if isinstance(raw, dict):
            return {
                "value": raw.get("value"),
                "confidence": float(raw.get("confidence", 0.5)),
                "evidence": raw.get("evidence", ""),
                "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
            }
        # Fallback: treat the whole response as the value with low confidence
        return {
            "value": str(raw),
            "confidence": 0.4,
            "evidence": "unstructured response",
            "metadata": {},
        }

    def parse_vision_response(self, response: Any) -> dict[str, Any]:
        """Parse a vision-model response payload into the enrichment shape."""
        return self.parse_ai_response(response)

    def score_confidence(self, parsed: dict[str, Any]) -> float:
        """Return the confidence score from a parsed AI response."""
        return max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))

    def merge_enrichment_candidates(
        self,
        *,
        field_name: str,
        original_data: dict[str, Any],
        image_parsed: dict[str, Any],
        text_parsed: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Merge image and text enrichment candidates with unified metadata."""
        text_parsed = text_parsed or {}

        image_value = image_parsed.get("value")
        text_value = text_parsed.get("value")

        image_confidence = self.score_confidence(image_parsed)
        text_confidence = self.score_confidence(text_parsed) if text_parsed else 0.0

        image_metadata = image_parsed.get("metadata") if isinstance(image_parsed, dict) else {}
        if not isinstance(image_metadata, dict):
            image_metadata = {}
        text_metadata = text_parsed.get("metadata") if isinstance(text_parsed, dict) else {}
        if not isinstance(text_metadata, dict):
            text_metadata = {}

        image_assets_raw = image_metadata.get("assets")
        source_assets = [
            str(asset)
            for asset in (image_assets_raw if isinstance(image_assets_raw, list) else [])
            if asset is not None
        ]

        has_image_value = image_value not in (None, "")
        has_text_value = text_value not in (None, "")

        if has_image_value and has_text_value:
            source_type = "hybrid"
            selected_value = image_value if image_confidence >= text_confidence else text_value
            confidence = max(image_confidence, text_confidence)
            reasoning = (
                f"Hybrid enrichment: image_analysis confidence={image_confidence:.2f}, "
                f"text_enrichment confidence={text_confidence:.2f}."
            )
            evidence = " | ".join(
                str(part)
                for part in [image_parsed.get("evidence", ""), text_parsed.get("evidence", "")]
                if part
            )
        elif has_image_value:
            source_type = "image_analysis"
            selected_value = image_value
            confidence = image_confidence
            reasoning = f"Image analysis selected with confidence={image_confidence:.2f}."
            evidence = str(image_parsed.get("evidence", ""))
        elif has_text_value:
            source_type = "text_enrichment"
            selected_value = text_value
            confidence = text_confidence
            reasoning = f"Text enrichment selected with confidence={text_confidence:.2f}."
            evidence = str(text_parsed.get("evidence", ""))
        else:
            source_type = "text_enrichment" if text_parsed else "image_analysis"
            selected_value = None
            confidence = max(image_confidence, text_confidence)
            reasoning = "No reliable value extracted from available enrichment sources."
            evidence = (
                " | ".join(
                    str(part)
                    for part in [image_parsed.get("evidence", ""), text_parsed.get("evidence", "")]
                    if part
                )
                or "enrichment unavailable"
            )

        return {
            "value": selected_value,
            "confidence": confidence,
            "evidence": evidence,
            "reasoning": reasoning,
            "source_type": source_type,
            "source_assets": source_assets,
            "original_data": original_data,
            "enriched_data": {field_name: selected_value},
            "metadata": {
                "source_type": source_type,
                "image": {
                    "confidence": image_confidence,
                    "assets_count": len(source_assets),
                },
                "text": {"confidence": text_confidence},
                "sources_used": [
                    source
                    for source, present in (
                        ("image_analysis", has_image_value),
                        ("text_enrichment", has_text_value),
                    )
                    if present
                ],
                "image_metadata": image_metadata,
                "text_metadata": text_metadata,
            },
        }

    def build_proposed_attribute(
        self,
        entity_id: str,
        field_name: str,
        parsed: dict[str, Any],
        *,
        model_id: str = "unknown",
        job_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Assemble a ProposedAttribute record ready for Cosmos DB."""
        confidence = self.score_confidence(parsed)
        status = "auto_approved" if confidence >= self.auto_approve_threshold else "pending"
        return {
            "id": str(uuid.uuid4()),
            "job_id": job_id or str(uuid.uuid4()),
            "entity_id": entity_id,
            "field_name": field_name,
            "proposed_value": parsed.get("value"),
            "confidence": confidence,
            "evidence": parsed.get("evidence", ""),
            "reasoning": parsed.get("reasoning", parsed.get("evidence", "")),
            "source_model": model_id,
            "source_type": parsed.get("source_type", "text_enrichment"),
            "source_assets": parsed.get("source_assets", []),
            "original_data": parsed.get("original_data", {field_name: None}),
            "enriched_data": parsed.get("enriched_data", {field_name: parsed.get("value")}),
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "confidence_metadata": parsed.get("metadata", {}),
        }

    def needs_hitl(self, proposed: dict[str, Any]) -> bool:
        """Return True when the attribute requires human review."""
        return proposed.get("status") == "pending"

    def build_audit_event(
        self,
        action: str,
        entity_id: str,
        field_name: str,
        proposed: dict[str, Any],
    ) -> dict[str, Any]:
        """Build an immutable audit event for an enrichment action."""
        return {
            "id": str(uuid.uuid4()),
            "action": action,
            "entity_id": entity_id,
            "field_name": field_name,
            "proposed_attribute_id": proposed.get("id"),
            "confidence": proposed.get("confidence"),
            "status": proposed.get("status"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
