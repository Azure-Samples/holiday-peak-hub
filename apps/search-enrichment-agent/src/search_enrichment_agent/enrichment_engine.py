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
        }

    def build_complex_fields(
        self,
        approved_truth: dict[str, Any],
        model_output: dict[str, Any],
    ) -> dict[str, Any]:
        simple = self.build_simple_fields(approved_truth)

        merged = dict(simple)
        for key in _REQUIRED_FIELDS:
            candidate = model_output.get(key)
            if key in {"use_cases", "complementary_products", "substitute_products", "search_keywords"}:
                normalized = self._normalize_string_list(candidate)
                if normalized:
                    merged[key] = normalized
            elif key == "enriched_description":
                text = str(candidate or "").strip()
                if text:
                    merged[key] = text

        return merged

    def validate_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Return the required field set with normalized values."""
        return {
            "use_cases": self._normalize_string_list(fields.get("use_cases")),
            "complementary_products": self._normalize_string_list(
                fields.get("complementary_products")
            ),
            "substitute_products": self._normalize_string_list(fields.get("substitute_products")),
            "search_keywords": self._normalize_string_list(fields.get("search_keywords")),
            "enriched_description": str(fields.get("enriched_description") or "").strip(),
        }

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
            "jacket": ["cold weather", "commuting", "outdoor"],
            "bag": ["travel", "daily carry", "organization"],
            "kitchen": ["home cooking", "meal prep", "kitchen organization"],
            "beauty": ["daily routine", "self care", "gift"],
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
