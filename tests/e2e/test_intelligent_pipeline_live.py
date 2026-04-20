"""Live integration tests for the intelligent search pipeline.

These tests hit the **real deployed services** (APIM → nginx → AKS pod →
AI Foundry + AI Search + CRUD) and validate:
  1. Wall-clock response time ≤ 5 s (the strict pipeline budget).
  2. Response shape: either valid results or a hard error — never a degraded
     fallback that hangs for tens of seconds.

Requirements:
  - The service must be deployed and reachable via APIM.
  - Set ``CATALOG_SEARCH_LIVE_URL`` env var to override the default APIM
    endpoint, or the test falls back to the dev APIM URL.

Run:
    pytest tests/e2e/test_intelligent_pipeline_live.py -m integration -v
"""

from __future__ import annotations

import os
import time

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_APIM_URL = (
    "https://holidaypeakhub405-dev-apim.azure-api.net"
    "/agents/ecommerce-catalog-search/invoke"
)

LIVE_URL = os.getenv("CATALOG_SEARCH_LIVE_URL", _DEFAULT_APIM_URL)

# The strict pipeline budget enforced by the agent code.
PIPELINE_BUDGET_SECONDS = 5.0

# We allow a small HTTP overhead on top of the pipeline budget for network
# round-trip, TLS handshake, and APIM policy evaluation.
HTTP_OVERHEAD_SECONDS = 3.0
MAX_WALL_CLOCK_SECONDS = PIPELINE_BUDGET_SECONDS + HTTP_OVERHEAD_SECONDS

# Per-request timeout — generous enough for the full stack but catches hangs.
REQUEST_TIMEOUT_SECONDS = 15.0

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ---------------------------------------------------------------------------
# Reachability gate
# ---------------------------------------------------------------------------


def _service_reachable() -> bool:
    """Quick connectivity check so we skip gracefully when offline."""
    try:
        resp = httpx.post(
            LIVE_URL,
            json={"query": "ping", "limit": 1, "mode": "keyword"},
            timeout=30.0,
        )
        # Any HTTP response (even 500) means the network path is live.
        return resp.status_code < 502
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError):
        return False


_reachable = _service_reachable()

skip_if_unreachable = pytest.mark.skipif(
    not _reachable,
    reason=f"Live service not reachable at {LIVE_URL}",
)

# ---------------------------------------------------------------------------
# Queries — 10 natural-language, conversational queries that exercise the
# intelligent pipeline (intent classification → sub-query fan-out → hybrid
# search → product resolution → ranking).
# ---------------------------------------------------------------------------

NATURAL_LANGUAGE_QUERIES: list[tuple[str, str]] = [
    (
        "travel_russia_clothes",
        "I'm traveling to Russia next month, which clothes should I get?",
    ),
    (
        "hiking_alps_gear",
        "What's the best gear for a week-long hike in the Swiss Alps?",
    ),
    (
        "winter_camping_warm",
        "I need something really warm for a winter camping trip in Canada",
    ),
    (
        "beach_vacation_thailand",
        "Suggest me outfits for a two-week beach vacation in Thailand",
    ),
    (
        "marathon_winter_shoes",
        "What running shoes are best for marathon training during winter?",
    ),
    (
        "business_trip_london",
        "I have a business trip to London in November, what should I pack?",
    ),
    (
        "kids_outdoor_summer",
        "Looking for durable outdoor clothing for kids playing in the summer heat",
    ),
    (
        "skiing_equipment_beginner",
        "I'm a beginner skier, what equipment and clothing do I need for my first trip?",
    ),
    (
        "rainy_commute_city",
        "Best waterproof jacket and shoes for commuting in a rainy city?",
    ),
    (
        "festival_weekend_outfit",
        "Help me pick a stylish but comfortable outfit for a music festival weekend",
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_payload(query: str, *, limit: int = 5) -> dict:
    return {
        "query": query,
        "limit": limit,
        "mode": "intelligent",
    }


def _assert_response_contract(body: dict, query: str) -> None:
    """Validate the response satisfies the strict pipeline contract."""
    # Must always contain these top-level keys
    assert "results" in body, f"Missing 'results' key for query: {query}"
    assert "mode" in body, f"Missing 'mode' key for query: {query}"

    result_type = body.get("result_type")
    error = body.get("error")

    if error == "intelligent_pipeline_timeout":
        # Hard error path — this is acceptable under the strict contract.
        assert body["results"] == [], (
            f"Hard error should have empty results for query: {query}"
        )
        assert body.get("degraded") is False, (
            f"Hard error must not be degraded for query: {query}"
        )
        assert result_type == "error", (
            f"Hard error result_type must be 'error', got '{result_type}' for query: {query}"
        )
    else:
        # Success path — we got actual search results.
        assert result_type != "degraded_fallback", (
            f"Got degraded_fallback — the old slow path leaked through for query: {query}"
        )
        # Results should be a list (may be empty if catalog has no matching items).
        assert isinstance(body["results"], list), (
            f"Results must be a list for query: {query}"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@skip_if_unreachable
@pytest.mark.parametrize(
    "query_id, query",
    NATURAL_LANGUAGE_QUERIES,
    ids=[q[0] for q in NATURAL_LANGUAGE_QUERIES],
)
async def test_intelligent_pipeline_completes_within_budget(
    query_id: str,
    query: str,
) -> None:
    """Each natural-language query must return within the wall-clock budget
    and satisfy the strict response contract (results or hard error, never a
    degraded hang).
    """
    payload = _build_payload(query)

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        t0 = time.monotonic()
        response = await client.post(
            LIVE_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        elapsed = time.monotonic() - t0

    assert response.status_code == 200, (
        f"[{query_id}] HTTP {response.status_code}: {response.text[:300]}"
    )

    body = response.json()
    _assert_response_contract(body, query)

    assert elapsed <= MAX_WALL_CLOCK_SECONDS, (
        f"[{query_id}] Pipeline took {elapsed:.2f}s (budget: {MAX_WALL_CLOCK_SECONDS:.1f}s). "
        f"result_type={body.get('result_type')}, error={body.get('error')}"
    )


@skip_if_unreachable
async def test_intelligent_pipeline_summary_report() -> None:
    """Run all 10 queries sequentially and produce a summary table.

    This test always passes (unless the service is down) — it's a diagnostic
    reporter so you can eyeball timing, result counts, and modes across all
    queries in one shot before deploying.
    """
    rows: list[dict] = []

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        for query_id, query in NATURAL_LANGUAGE_QUERIES:
            payload = _build_payload(query)
            t0 = time.monotonic()
            try:
                response = await client.post(
                    LIVE_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                elapsed = time.monotonic() - t0
                if response.status_code == 200:
                    body = response.json()
                    rows.append({
                        "query_id": query_id,
                        "elapsed_s": round(elapsed, 2),
                        "http": response.status_code,
                        "mode": body.get("mode"),
                        "result_type": body.get("result_type"),
                        "results": len(body.get("results", [])),
                        "error": body.get("error"),
                        "intent": (body.get("intent") or {}).get("intent"),
                        "within_budget": elapsed <= MAX_WALL_CLOCK_SECONDS,
                    })
                else:
                    rows.append({
                        "query_id": query_id,
                        "elapsed_s": round(elapsed, 2),
                        "http": response.status_code,
                        "mode": None,
                        "result_type": None,
                        "results": 0,
                        "error": response.text[:120],
                        "intent": None,
                        "within_budget": False,
                    })
            except Exception as exc:  # noqa: BLE001
                elapsed = time.monotonic() - t0
                rows.append({
                    "query_id": query_id,
                    "elapsed_s": round(elapsed, 2),
                    "http": None,
                    "mode": None,
                    "result_type": None,
                    "results": 0,
                    "error": str(exc)[:120],
                    "intent": None,
                    "within_budget": False,
                })

    # ── Pretty-print summary ──
    header = (
        f"{'Query':<30} {'Time':>6} {'HTTP':>4} {'Mode':<14} "
        f"{'Type':<20} {'#Res':>4} {'Budget':>6} {'Intent':<20}"
    )
    sep = "-" * len(header)
    lines = ["\n" + sep, header, sep]
    for r in rows:
        budget_flag = "OK" if r["within_budget"] else "OVER"
        lines.append(
            f"{r['query_id']:<30} {r['elapsed_s']:>5.2f}s {r['http'] or 'ERR':>4} "
            f"{(r['mode'] or '-'):<14} {(r['result_type'] or '-'):<20} "
            f"{r['results']:>4} {budget_flag:>6} {(r['intent'] or '-'):<20}"
        )
    lines.append(sep)

    passed = sum(1 for r in rows if r["within_budget"])
    lines.append(f"Within budget: {passed}/{len(rows)}")
    lines.append(sep)

    print("\n".join(lines))

    # Soft assertion — don't fail CI, but surface the data.
    assert len(rows) == len(NATURAL_LANGUAGE_QUERIES)
