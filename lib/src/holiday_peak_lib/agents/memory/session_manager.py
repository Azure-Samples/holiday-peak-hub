"""Smart session management: continuity decisions, summaries, and Cosmos persistence.

Architecture:
- **Redis (hot)**: Compact session summary (keywords, message count, last topic).
  Used for fast decision-making on whether to continue a Foundry thread.
- **Cosmos (warm)**: Full session state (message history + Foundry session dict).
  Used to restore sessions for continuation. IDs match Foundry's session_id.
- **Foundry**: Thread continuation via AgentSession with the SAME session_id
  stored in Cosmos.

Decision flow:
1. Agent receives request → extract entity_id and intent keywords.
2. Lookup Redis summary for this service:entity pair.
3. If summary exists AND keywords overlap → CONTINUE (fetch session from Cosmos).
4. If no summary or keywords diverge → FRESH session (new session_id).
5. After model invocation → update Redis summary, upsert Cosmos full session.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionSummary:
    """Compact representation stored in Redis for fast continuity decisions."""

    session_id: str
    service: str
    entity_id: str
    topic_keywords: list[str]
    message_count: int
    last_epoch: float
    summary_text: str


@dataclass(frozen=True)
class SessionDecision:
    """Result of evaluating whether to continue or start fresh."""

    continue_session: bool
    session_id: str
    foundry_session_state: dict[str, Any] | None = field(default=None)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUMMARY_KEY_PREFIX = "session_summary"
_KEYWORD_OVERLAP_THRESHOLD = 0.3  # 30% keyword overlap triggers continuation
_MAX_SESSION_MESSAGES = 20  # After this, start fresh to avoid context bloat
_STALE_SECONDS = 1800  # 30 min idle = stale session
_STOP_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "dare",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "only",
        "own",
        "same",
        "than",
        "too",
        "very",
        "just",
        "because",
        "about",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "what",
        "which",
        "who",
        "whom",
        "when",
        "where",
        "why",
        "how",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
    }
)


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------


def extract_keywords(text: str, *, max_keywords: int = 12) -> list[str]:
    """Extract meaningful keywords from text by removing stop words."""
    if not text:
        return []
    tokens = re.findall(r"[a-z0-9_-]+", text.lower())
    keywords = [t for t in tokens if t not in _STOP_WORDS and len(t) > 2]
    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique[:max_keywords]


def compute_keyword_overlap(existing: list[str], incoming: list[str]) -> float:
    """Compute Jaccard-like overlap between two keyword sets."""
    if not existing or not incoming:
        return 0.0
    set_a = set(existing)
    set_b = set(incoming)
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


# ---------------------------------------------------------------------------
# Redis summary key
# ---------------------------------------------------------------------------


def _summary_redis_key(service: str, entity_id: str) -> str:
    # If entity_id already contains service prefix (from inject_session_id),
    # use it directly to avoid duplication.
    if entity_id.startswith(f"{service}:"):
        return f"{_SUMMARY_KEY_PREFIX}:{entity_id}"
    return f"{_SUMMARY_KEY_PREFIX}:{service}:{entity_id}"


# ---------------------------------------------------------------------------
# Core decision logic
# ---------------------------------------------------------------------------


async def evaluate_session_continuity(
    hot_memory: Any | None,
    warm_memory: Any | None,
    request: dict[str, Any],
    *,
    service: str,
    entity_id: str,
) -> SessionDecision:
    """Decide whether to continue an existing Foundry session or start fresh.

    Decision rules:
    1. No summary in Redis → FRESH (new session_id).
    2. Summary exists but stale (>30 min idle) → FRESH.
    3. Summary exists but message_count > threshold → FRESH (prevent bloat).
    4. Summary exists and keyword overlap >= threshold → CONTINUE.
    5. Summary exists but keywords diverge → FRESH.

    On CONTINUE, fetches full session state from Cosmos to pass to Foundry.
    """
    if hot_memory is None:
        return SessionDecision(
            continue_session=False,
            session_id=entity_id,
        )

    redis_key = _summary_redis_key(service, entity_id)
    raw_summary = await hot_memory.get(redis_key)

    if not raw_summary:
        return SessionDecision(
            continue_session=False,
            session_id=f"{service}:{entity_id}:{int(time.time())}",
        )

    # Parse stored summary
    try:
        summary_data = json.loads(raw_summary) if isinstance(raw_summary, str) else raw_summary
        summary = SessionSummary(**summary_data)
    except (TypeError, ValueError, KeyError):
        return SessionDecision(
            continue_session=False,
            session_id=f"{service}:{entity_id}:{int(time.time())}",
        )

    # Staleness check
    elapsed = time.time() - summary.last_epoch
    if elapsed > _STALE_SECONDS:
        return SessionDecision(
            continue_session=False,
            session_id=f"{service}:{entity_id}:{int(time.time())}",
        )

    # Message count threshold
    if summary.message_count >= _MAX_SESSION_MESSAGES:
        return SessionDecision(
            continue_session=False,
            session_id=f"{service}:{entity_id}:{int(time.time())}",
        )

    # Keyword overlap decision
    request_text = _extract_request_text(request)
    incoming_keywords = extract_keywords(request_text)
    overlap = compute_keyword_overlap(summary.topic_keywords, incoming_keywords)

    if overlap < _KEYWORD_OVERLAP_THRESHOLD:
        return SessionDecision(
            continue_session=False,
            session_id=f"{service}:{entity_id}:{int(time.time())}",
        )

    # CONTINUE: fetch full session from Cosmos
    foundry_state = None
    if warm_memory is not None:
        try:
            cosmos_session = await warm_memory.read(
                item_id=summary.session_id,
                partition_key=f"{service}:{entity_id}",
            )
            if cosmos_session and "foundry_session_state" in cosmos_session:
                foundry_state = cosmos_session["foundry_session_state"]
        except Exception as exc:  # noqa: BLE001 — fail-open on Cosmos read
            logger.warning(
                "session_continuity_cosmos_read_failed "
                "session_id=%s service=%s entity_id=%s error=%s",
                summary.session_id,
                service,
                entity_id,
                exc,
            )

    return SessionDecision(
        continue_session=True,
        session_id=summary.session_id,
        foundry_session_state=foundry_state,
    )


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------


def build_session_summary(
    *,
    session_id: str,
    service: str,
    entity_id: str,
    messages: list[dict[str, Any]],
    result: dict[str, Any],
    prior_summary: SessionSummary | None = None,
) -> SessionSummary:
    """Build a compact session summary from the interaction.

    Merges with prior summary keywords to maintain topic continuity.
    """
    # Collect text from messages and result for keyword extraction
    texts: list[str] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, dict):
            texts.append(json.dumps(content, default=str))
        elif isinstance(content, str):
            texts.append(content)

    result_content = result.get("content", "")
    if isinstance(result_content, str):
        texts.append(result_content)

    combined_text = " ".join(texts)
    new_keywords = extract_keywords(combined_text)

    # Merge with prior keywords (keep most recent + overlapping)
    if prior_summary:
        merged = list(prior_summary.topic_keywords)
        for kw in new_keywords:
            if kw not in merged:
                merged.append(kw)
        topic_keywords = merged[-15:]  # cap at 15 most recent
        message_count = prior_summary.message_count + len(messages)
    else:
        topic_keywords = new_keywords
        message_count = len(messages)

    # Build compact summary text (last assistant response truncated)
    summary_text = (result_content[:200] + "...") if len(result_content) > 200 else result_content

    return SessionSummary(
        session_id=session_id,
        service=service,
        entity_id=entity_id,
        topic_keywords=topic_keywords,
        message_count=message_count,
        last_epoch=time.time(),
        summary_text=summary_text,
    )


# ---------------------------------------------------------------------------
# Persistence: Redis summary + Cosmos full session
# ---------------------------------------------------------------------------


async def store_summary(
    hot_memory: Any | None,
    summary: SessionSummary,
    *,
    ttl_seconds: int = 1800,
) -> None:
    """Store the session summary in Redis."""
    if hot_memory is None:
        return
    redis_key = _summary_redis_key(summary.service, summary.entity_id)
    payload = json.dumps(asdict(summary), default=str)
    await hot_memory.set(key=redis_key, value=payload, ttl_seconds=ttl_seconds)


async def persist_full_session(
    warm_memory: Any | None,
    *,
    session_id: str,
    service: str,
    entity_id: str,
    foundry_session_state: dict[str, Any] | None,
    messages: list[dict[str, Any]],
    summary_text: str,
) -> None:
    """Persist the full session to Cosmos DB.

    The document ID matches the Foundry session_id so both systems
    reference the same thread identity.
    """
    if warm_memory is None or foundry_session_state is None:
        return
    document = {
        "id": session_id,
        "partition_key": f"{service}:{entity_id}",
        "service": service,
        "entity_id": entity_id,
        "foundry_session_state": foundry_session_state,
        "messages": messages[-_MAX_SESSION_MESSAGES:],  # Trim to prevent bloat
        "summary": summary_text,
        "updated_epoch": time.time(),
    }
    try:
        await warm_memory.upsert(document)
    except Exception as exc:  # noqa: BLE001 — fail-open on Cosmos write
        logger.warning(
            "session_persistence_cosmos_write_failed "
            "session_id=%s service=%s entity_id=%s error=%s",
            session_id,
            service,
            entity_id,
            exc,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_request_text(request: dict[str, Any]) -> str:
    """Extract searchable text from a request dict for keyword comparison."""
    parts: list[str] = []
    for key in ("query", "question", "prompt", "message", "intent", "content"):
        val = request.get(key)
        if isinstance(val, str):
            parts.append(val)
    # Also include entity-related fields as context
    for key in ("entity_id", "sku", "tracking_id", "order_id", "product_name", "category"):
        val = request.get(key)
        if val:
            parts.append(str(val))
    return " ".join(parts)
