"""Search enrichment engine for approved truth data."""

from __future__ import annotations

from typing import Any

_REQUIRED_FIELDS = {
    "use_cases",
    "complementary_products",
    "substitute_products",
    "search_keywords",
    "enriched_description",
}

_AMPLIFICATION_FIELDS = {
    "marketing_bullets",
    "seo_title",
    "target_audience",
    "seasonal_relevance",
    "facet_tags",
    "sustainability_signals",
    "care_guidance",
    "completeness_pct",
}


class SearchEnrichmentEngine:
    """Generate search-focused enrichment fields from approved truth data.

    The engine follows a strategy-style split:
    - simple strategy: deterministic local generation
    - complex strategy: merge deterministic output with model-assisted output
    """

    def is_complex(self, approved_truth: dict[str, Any]) -> bool:
        text = str(approved_truth.get("description") or "")
        features = approved_truth.get("features")
        feature_count = len(features) if isinstance(features, list) else 0
        return len(text.split()) > 30 or feature_count > 3

    def build_simple_fields(self, approved_truth: dict[str, Any]) -> dict[str, Any]:
        name = str(
            approved_truth.get("name")
            or approved_truth.get("title")
            or approved_truth.get("product_name")
            or approved_truth.get("sku")
            or "Product"
        )
        category = str(approved_truth.get("category") or "product")
        brand = str(approved_truth.get("brand") or "")
        description = str(approved_truth.get("description") or "").strip()

        explicit_use_cases = approved_truth.get("use_cases")
        use_cases = self._normalize_string_list(explicit_use_cases)
        if not use_cases:
            use_cases = self._infer_use_cases(category=category, description=description)

        complementary_products = self._normalize_string_list(
            approved_truth.get("complementary_products")
            or approved_truth.get("complements")
            or approved_truth.get("cross_sell")
        )
        substitute_products = self._normalize_string_list(
            approved_truth.get("substitute_products")
            or approved_truth.get("substitutes")
            or approved_truth.get("alternatives")
        )

        keywords = self._build_keywords(approved_truth)
        enriched_description = self._build_description(
            name=name,
            category=category,
            brand=brand,
            description=description,
            use_cases=use_cases,
            keywords=keywords,
        )

        return {
            "use_cases": use_cases,
            "complementary_products": complementary_products,
            "substitute_products": substitute_products,
            "search_keywords": keywords,
            "enriched_description": enriched_description,
            **self._build_amplification_fields(approved_truth, name, category, brand, keywords),
        }

    def build_complex_fields(
        self,
        approved_truth: dict[str, Any],
        model_output: dict[str, Any],
    ) -> dict[str, Any]:
        simple = self.build_simple_fields(approved_truth)

        merged = dict(simple)
        for key in _REQUIRED_FIELDS | _AMPLIFICATION_FIELDS:
            candidate = model_output.get(key)
            if key in {
                "use_cases",
                "complementary_products",
                "substitute_products",
                "search_keywords",
                "marketing_bullets",
                "target_audience",
                "seasonal_relevance",
                "facet_tags",
                "sustainability_signals",
            }:
                normalized = self._normalize_string_list(candidate)
                if normalized:
                    merged[key] = normalized
            elif key in {"enriched_description", "seo_title", "care_guidance"}:
                text = str(candidate or "").strip()
                if text:
                    merged[key] = text
            elif key == "completeness_pct":
                if isinstance(candidate, (int, float)):
                    merged[key] = max(0.0, min(1.0, float(candidate)))

        return merged

    def validate_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Return the required + amplification field set with normalized values."""
        result = {
            "use_cases": self._normalize_string_list(fields.get("use_cases")),
            "complementary_products": self._normalize_string_list(
                fields.get("complementary_products")
            ),
            "substitute_products": self._normalize_string_list(fields.get("substitute_products")),
            "search_keywords": self._normalize_string_list(fields.get("search_keywords")),
            "enriched_description": str(fields.get("enriched_description") or "").strip(),
            "marketing_bullets": self._normalize_string_list(fields.get("marketing_bullets")),
            "seo_title": str(fields.get("seo_title") or "").strip() or None,
            "target_audience": self._normalize_string_list(fields.get("target_audience")),
            "seasonal_relevance": self._normalize_string_list(fields.get("seasonal_relevance")),
            "facet_tags": self._normalize_string_list(fields.get("facet_tags")),
            "sustainability_signals": self._normalize_string_list(
                fields.get("sustainability_signals")
            ),
            "care_guidance": str(fields.get("care_guidance") or "").strip() or None,
        }
        pct = fields.get("completeness_pct")
        result["completeness_pct"] = (
            max(0.0, min(1.0, float(pct))) if isinstance(pct, (int, float)) else None
        )
        return result

    # ------------------------------------------------------------------
    # Amplification dimensions
    # ------------------------------------------------------------------

    def _build_amplification_fields(
        self,
        approved_truth: dict[str, Any],
        name: str,
        category: str,
        brand: str,
        keywords: list[str],
    ) -> dict[str, Any]:
        """Generate deterministic amplification fields from approved truth."""
        description = str(approved_truth.get("description") or "").strip()
        features = self._normalize_string_list(approved_truth.get("features"))
        material = str(approved_truth.get("material") or "")

        return {
            "marketing_bullets": self._build_marketing_bullets(name, brand, features, description),
            "seo_title": self._build_seo_title(name, brand, category),
            "target_audience": self._infer_target_audience(approved_truth, category),
            "seasonal_relevance": self._infer_seasonal_relevance(category, keywords),
            "facet_tags": self._build_facet_tags(approved_truth),
            "sustainability_signals": self._detect_sustainability_signals(approved_truth, material),
            "care_guidance": self._build_care_guidance(approved_truth),
            "completeness_pct": self._compute_completeness(approved_truth),
        }

    def _build_marketing_bullets(
        self,
        name: str,
        brand: str,
        features: list[str],
        description: str,
    ) -> list[str]:
        bullets: list[str] = []
        if brand:
            bullets.append(f"Trusted quality from {brand}")
        for feat in features[:5]:
            text = feat.strip()
            if text and len(text) > 3:
                bullets.append(text[0].upper() + text[1:])
        if not bullets and description:
            sentences = [s.strip() for s in description.replace(".", ".|").split("|") if s.strip()]
            bullets = sentences[:3]
        return bullets

    def _build_seo_title(self, name: str, brand: str, category: str) -> str:
        parts = [p for p in [name, brand, category] if p and p.lower() not in ("product",)]
        title = " - ".join(parts[:3])
        return title[:70] if title else name

    def _infer_target_audience(self, approved_truth: dict[str, Any], category: str) -> list[str]:
        audience: list[str] = []
        gender = str(approved_truth.get("gender") or "").lower()
        age = str(approved_truth.get("age_group") or approved_truth.get("age_range") or "").lower()
        text = f"{category} {gender} {age}".lower()

        if gender in ("men", "male"):
            audience.append("men")
        elif gender in ("women", "female"):
            audience.append("women")
        elif gender in ("kids", "children", "boys", "girls"):
            audience.append("kids")

        if age and age not in ("", "none"):
            audience.append(age)

        audience_map = {
            "baby": ["parents", "caregivers"],
            "toy": ["families", "kids"],
            "pet": ["pet owners"],
            "office": ["professionals", "students"],
            "beauty": ["beauty enthusiasts"],
            "sport": ["athletes", "fitness enthusiasts"],
            "electronics": ["tech enthusiasts"],
        }
        for marker, segments in audience_map.items():
            if marker in text:
                audience.extend(s for s in segments if s not in audience)
                break

        return audience or ["general consumers"]

    def _infer_seasonal_relevance(self, category: str, keywords: list[str]) -> list[str]:
        text = f"{category} {' '.join(keywords)}".lower()
        seasons: list[str] = []

        summer_signals = {"summer", "beach", "pool", "sunscreen", "outdoor", "sandal", "swim"}
        winter_signals = {"winter", "cold", "snow", "insulated", "thermal", "heated", "fleece"}
        holiday_signals = {"gift", "holiday", "christmas", "valentine", "halloween", "easter"}
        back_to_school = {"school", "backpack", "notebook", "pencil", "stationery"}

        tokens = set(text.split())
        if tokens & summer_signals:
            seasons.append("summer")
        if tokens & winter_signals:
            seasons.append("winter")
        if tokens & holiday_signals:
            seasons.append("holiday-season")
        if tokens & back_to_school:
            seasons.append("back-to-school")

        return seasons or ["year-round"]

    def _build_facet_tags(self, approved_truth: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        facet_keys = (
            "brand",
            "category",
            "color",
            "material",
            "size",
            "gender",
            "sport_type",
            "pet_type",
            "age_group",
            "style",
        )
        for key in facet_keys:
            val = approved_truth.get(key)
            if val is None:
                continue
            if isinstance(val, list):
                for item in val:
                    tag = f"{key}:{str(item).strip().lower()}"
                    if tag not in tags:
                        tags.append(tag)
            else:
                tag = f"{key}:{str(val).strip().lower()}"
                if tag not in tags:
                    tags.append(tag)

        price = approved_truth.get("price")
        if isinstance(price, (int, float)):
            if price < 25:
                tags.append("price:budget")
            elif price < 100:
                tags.append("price:mid-range")
            elif price < 500:
                tags.append("price:premium")
            else:
                tags.append("price:luxury")

        return tags

    _SUSTAINABILITY_TERMS = frozenset(
        {
            "organic",
            "recycled",
            "sustainable",
            "eco-friendly",
            "biodegradable",
            "compostable",
            "bamboo",
            "hemp",
            "fair-trade",
            "vegan",
            "cruelty-free",
            "bpa-free",
            "non-toxic",
            "plant-based",
            "renewable",
            "fsc-certified",
        }
    )

    def _detect_sustainability_signals(
        self, approved_truth: dict[str, Any], material: str
    ) -> list[str]:
        signals: list[str] = []
        searchable = " ".join(
            str(v)
            for v in (
                material,
                approved_truth.get("description", ""),
                " ".join(self._normalize_string_list(approved_truth.get("features"))),
                approved_truth.get("ingredients", ""),
            )
        ).lower()

        for term in sorted(self._SUSTAINABILITY_TERMS):
            if term in searchable:
                signals.append(term)

        if approved_truth.get("organic") is True:
            if "organic" not in signals:
                signals.append("organic")
        if approved_truth.get("cruelty_free") is True:
            if "cruelty-free" not in signals:
                signals.append("cruelty-free")
        if approved_truth.get("eco_certified") is True:
            signals.append("eco-certified")

        return signals

    def _build_care_guidance(self, approved_truth: dict[str, Any]) -> str | None:
        care = approved_truth.get("care_instructions")
        if care:
            return str(care).strip()

        material = str(approved_truth.get("material") or "").lower()
        care_map = {
            "leather": "Wipe clean with a damp cloth. Condition regularly to maintain suppleness.",
            "cotton": "Machine wash cold. Tumble dry low.",
            "wool": "Hand wash or dry clean. Lay flat to dry.",
            "silk": "Dry clean only. Store in a cool, dry place.",
            "stainless_steel": "Wipe with a soft cloth. Avoid abrasive cleaners.",
            "wood": "Dust regularly. Avoid prolonged moisture exposure.",
        }
        for mat, guidance in care_map.items():
            if mat in material:
                return guidance
        return None

    _COMPLETENESS_CORE_KEYS = (
        "name",
        "brand",
        "category",
        "description",
        "price",
    )

    def _compute_completeness(self, approved_truth: dict[str, Any]) -> float:
        total = len(self._COMPLETENESS_CORE_KEYS)
        present = sum(
            1
            for k in self._COMPLETENESS_CORE_KEYS
            if approved_truth.get(k) not in (None, "", [], {})
        )
        features = approved_truth.get("features")
        if isinstance(features, list) and features:
            present += 1
        total += 1

        images = approved_truth.get("images") or approved_truth.get("media")
        if isinstance(images, list) and images:
            present += 1
        total += 1

        return round(present / total, 2) if total > 0 else 0.0

    # ------------------------------------------------------------------
    # Existing helpers
    # ------------------------------------------------------------------

    def _build_keywords(self, approved_truth: dict[str, Any]) -> list[str]:
        candidates: list[str] = []
        for key in (
            "name",
            "title",
            "brand",
            "category",
            "material",
            "color",
            "style",
            "description",
            "sport_type",
            "gender",
            "instrument_type",
            "pet_type",
            "dosage_form",
            "gemstone",
        ):
            value = approved_truth.get(key)
            if value is None:
                continue
            candidates.extend(str(value).replace("/", " ").replace("-", " ").split())

        for value in self._normalize_string_list(approved_truth.get("features")):
            candidates.extend(value.split())

        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "that",
            "this",
            "your",
            "into",
            "when",
            "more",
            "less",
            "in",
            "on",
            "of",
            "to",
            "a",
            "an",
        }

        deduped: list[str] = []
        seen: set[str] = set()
        for raw in candidates:
            token = raw.strip().lower()
            if len(token) < 3 or token in stopwords:
                continue
            if token in seen:
                continue
            seen.add(token)
            deduped.append(token)
            if len(deduped) >= 20:
                break
        return deduped

    def _build_description(
        self,
        *,
        name: str,
        category: str,
        brand: str,
        description: str,
        use_cases: list[str],
        keywords: list[str],
    ) -> str:
        components = [f"{name} is a {category} item"]
        if brand:
            components.append(f"from {brand}")
        if description:
            components.append(description)
        if use_cases:
            components.append(f"Ideal for: {', '.join(use_cases[:3])}.")
        if keywords:
            components.append(f"Search terms: {', '.join(keywords[:8])}.")
        return " ".join(part.strip() for part in components if part).strip()

    def _infer_use_cases(self, *, category: str, description: str) -> list[str]:
        text = f"{category} {description}".lower()
        category_map = {
            "shoe": ["daily wear", "walking", "outdoor"],
            "footwear": ["daily wear", "walking", "outdoor"],
            "jacket": ["cold weather", "commuting", "outdoor"],
            "bag": ["travel", "daily carry", "organization"],
            "kitchen": ["home cooking", "meal prep", "kitchen organization"],
            "beauty": ["daily routine", "self care", "gift"],
            "cosmetic": ["daily routine", "self care", "gift"],
            "electronics": ["productivity", "entertainment", "connected living"],
            "furniture": ["home decor", "comfort", "organization"],
            "sport": ["fitness", "training", "outdoor recreation"],
            "outdoor": ["camping", "hiking", "adventure"],
            "toy": ["play", "learning", "family time"],
            "game": ["entertainment", "family time", "learning"],
            "book": ["reading", "learning", "gift"],
            "jewelry": ["accessorizing", "gift", "special occasions"],
            "watch": ["daily wear", "timekeeping", "gift"],
            "food": ["cooking", "entertaining", "gifting"],
            "gourmet": ["cooking", "entertaining", "gifting"],
            "pet": ["pet care", "pet training", "pet comfort"],
            "auto": ["vehicle maintenance", "DIY repair", "road safety"],
            "garden": ["landscaping", "outdoor living", "gardening"],
            "office": ["workspace organization", "productivity", "school"],
            "health": ["wellness", "daily health", "recovery"],
            "baby": ["infant care", "parenting", "nursery"],
            "apparel": ["daily wear", "seasonal fashion", "layering"],
            "clothing": ["daily wear", "seasonal fashion", "layering"],
            "appliance": ["home convenience", "energy saving", "daily chores"],
            "instrument": ["music practice", "performance", "creative expression"],
        }
        for marker, use_cases in category_map.items():
            if marker in text:
                return use_cases
        return ["everyday use", "seasonal shopping"]

    def _normalize_string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, list):
            result: list[str] = []
            for item in value:
                text = str(item).strip()
                if text:
                    result.append(text)
            return result
        return [str(value).strip()] if str(value).strip() else []
