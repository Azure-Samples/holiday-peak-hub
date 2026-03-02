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

    def parse_ai_response(self, raw: Any) -> dict[str, Any]:
        """Parse AI response into structured proposed attribute fields."""
        if isinstance(raw, dict):
            return {
                "value": raw.get("value"),
                "confidence": float(raw.get("confidence", 0.5)),
                "evidence": raw.get("evidence", ""),
            }
        # Fallback: treat the whole response as the value with low confidence
        return {"value": str(raw), "confidence": 0.4, "evidence": "unstructured response"}

    def score_confidence(self, parsed: dict[str, Any]) -> float:
        """Return the confidence score from a parsed AI response."""
        return max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))

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
            "source_model": model_id,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
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
