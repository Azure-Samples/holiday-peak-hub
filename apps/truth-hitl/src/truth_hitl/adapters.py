"""Adapters for the Truth HITL service."""

from __future__ import annotations

from dataclasses import dataclass, field

from truth_hitl.review_manager import ReviewManager


@dataclass
class HITLAdapters:
    """Container for Truth HITL service adapters."""

    review_manager: ReviewManager = field(default_factory=ReviewManager)


def build_hitl_adapters(
    *,
    review_manager: ReviewManager | None = None,
) -> HITLAdapters:
    """Create adapters for the HITL review workflow."""
    return HITLAdapters(
        review_manager=review_manager or ReviewManager(),
    )
