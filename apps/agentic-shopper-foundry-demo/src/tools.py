from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

from pydantic import Field

from .telemetry.trace import trace_tool


_DATA = Path(__file__).resolve().parent.parent / "sample_data" / "products.json"


def _load_products() -> list[dict]:
    return json.loads(_DATA.read_text(encoding="utf-8"))


def _find_by_sku(sku: str) -> Optional[dict]:
    for p in _load_products():
        if p.get("sku") == sku:
            return p
    return None


@trace_tool("rank_products")
def rank_products(
    query: Annotated[str, Field(description="User intent + constraints (weather, activity, budget, fit).")],
    category: Annotated[Optional[str], Field(description="Category like shell-jackets, insulation, etc.")] = None,
) -> str:
    """Assortment/ranking API (demo).

    In a customer deployment, this would call a real ranking service. In this demo,
    we do a simple keyword match over the sample catalog.
    """
    q = (query or "").lower()
    products = _load_products()
    if category:
        products = [p for p in products if p.get("category") == category]

    def score(p: dict) -> int:
        text = " ".join([p.get("name", ""), " ".join(p.get("highlights", [])), p.get("notes", "")]).lower()
        s = 0
        for token in ["rain", "wet", "shell", "wind", "breath", "pack", "warm", "midlayer", "run", "active"]:
            if token in q and token in text:
                s += 2
        # slight bias toward lower price in demo
        s += max(0, 350 - int(p.get("price", 0))) // 50
        return s

    ranked = sorted(products, key=score, reverse=True)
    top = [p["sku"] for p in ranked[:3]]
    return f"Top ranked SKUs: {top}"


@trace_tool("get_availability")
def get_availability(
    sku: Annotated[str, Field(description="SKU to check")],
    size: Annotated[Optional[str], Field(description="Requested size (S/M/L/XL)")] = None,
    color: Annotated[Optional[str], Field(description="Requested color")] = None,
) -> str:
    """Availability/OMS API (demo).

    In production, this should query the OMS/inventory system. In this demo,
    we simulate availability based on the sample catalog.
    """
    p = _find_by_sku(sku)
    if not p:
        return f"Availability for {sku}: Unknown SKU."

    sizes = p.get("sizes", [])
    colors = p.get("colors", [])

    size_ok = (size in sizes) if size else True
    color_ok = (color in colors) if color else True

    if not size_ok:
        return f"Availability for {sku}: Not available in size={size}. Available sizes={sizes}."
    if not color_ok:
        return f"Availability for {sku}: Not available in color={color}. Available colors={colors}."

    size_part = f"size={size}" if size else f"sizes={','.join(sizes)}"
    color_part = f", color={color}" if color else ""
    return f"Availability for {sku}: In stock ({size_part}{color_part})."


@trace_tool("get_personalized_picks")
def get_personalized_picks(
    user_segment: Annotated[Optional[str], Field(description="Segment like trail-runner, ski, casual")] = None,
) -> str:
    """Personalization API (demo).

    In production, this should call the customer personalization service.
    Here we return a predictable subset for demos.
    """
    if user_segment:
        seg = user_segment.lower()
        if "run" in seg:
            return "Personalized picks: [FLEECE-020, SHELL-001]"
        if "hike" in seg or "trail" in seg:
            return "Personalized picks: [SHELL-014, FLEECE-020]"
    return "Personalized picks: [SHELL-014, INSUL-044]"
