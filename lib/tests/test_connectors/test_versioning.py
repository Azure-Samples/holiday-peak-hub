"""Tests for connector protocol versioning and interface evolution (issue #82)."""

from __future__ import annotations

from typing import Any

import pytest
from holiday_peak_lib.connectors.common.versioning import (
    BaseConnectorProtocol,
    FieldSpec,
    PIMConnectorProtocol_v1,
    PIMConnectorProtocol_v2,
    ProtocolDiff,
    ProtocolVersion,
    VersionedAdapter,
    diff_protocols,
    negotiate_version,
    register_protocol,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


class ConcretePIMv2(PIMConnectorProtocol_v2):
    """Minimal concrete v2 implementation for tests."""

    async def get_product(self, product_id: str) -> dict[str, Any]:
        return {
            "product_id": product_id,
            "name": "Test Product",
            "sku": "SKU-001",
            "category": "electronics",
            "taxonomy_path": ["electronics", "headphones"],
            "extended_attrs": {"color": "black"},
            "variants": [{"id": "v1"}],
            "lifecycle_status": "active",
        }

    async def list_products(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return [await self.get_product(f"P-{i}") for i in range(offset, offset + min(limit, 2))]

    async def get_product_variants(self, product_id: str) -> list[dict[str, Any]]:
        return [{"id": "v1", "color": "black"}]

    async def search_products(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        return [await self.get_product("P-SEARCH")]


# ---------------------------------------------------------------------------
# ProtocolVersion tests
# ---------------------------------------------------------------------------


class TestProtocolVersion:
    def test_str_representation(self):
        assert str(ProtocolVersion(1, 0)) == "v1.0"
        assert str(ProtocolVersion(2, 3)) == "v2.3"

    def test_repr(self):
        assert repr(ProtocolVersion(1, 0)) == "ProtocolVersion(1, 0)"

    def test_equality(self):
        assert ProtocolVersion(1, 0) == ProtocolVersion(1, 0)
        assert ProtocolVersion(1, 0) != ProtocolVersion(2, 0)

    def test_ordering(self):
        assert ProtocolVersion(1, 0) < ProtocolVersion(2, 0)
        assert ProtocolVersion(1, 0) < ProtocolVersion(1, 1)
        assert ProtocolVersion(2, 0) > ProtocolVersion(1, 5)
        assert ProtocolVersion(1, 0) <= ProtocolVersion(1, 0)
        assert ProtocolVersion(2, 0) >= ProtocolVersion(1, 5)

    def test_hashable(self):
        s = {ProtocolVersion(1, 0), ProtocolVersion(2, 0), ProtocolVersion(1, 0)}
        assert len(s) == 2

    def test_compatibility_same_major(self):
        assert ProtocolVersion(1, 0).is_compatible_with(ProtocolVersion(1, 5))
        assert ProtocolVersion(1, 5).is_compatible_with(ProtocolVersion(1, 0))

    def test_compatibility_different_major(self):
        assert not ProtocolVersion(1, 0).is_compatible_with(ProtocolVersion(2, 0))

    def test_negative_values_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            ProtocolVersion(-1, 0)


# ---------------------------------------------------------------------------
# FieldSpec tests
# ---------------------------------------------------------------------------


class TestFieldSpec:
    def test_required_field(self):
        f = FieldSpec("product_id", "str")
        assert f.name == "product_id"
        assert f.required is True
        assert f.deprecated is False
        assert f.added_in is None

    def test_optional_versioned_field(self):
        f = FieldSpec("variants", "list[dict]", required=False, added_in=ProtocolVersion(2, 0))
        assert f.required is False
        assert f.added_in == ProtocolVersion(2, 0)


# ---------------------------------------------------------------------------
# ProtocolDiff tests
# ---------------------------------------------------------------------------


class TestProtocolDiff:
    def test_summary_no_changes(self):
        diff = ProtocolDiff()
        assert diff.summary() == "no changes"

    def test_summary_with_additions(self):
        diff = ProtocolDiff(added=["taxonomy_path", "variants"])
        assert "+2 added" in diff.summary()

    def test_summary_with_removal_is_breaking(self):
        diff = ProtocolDiff(removed=["sku"])
        assert diff.is_breaking() is True
        assert "breaking" in diff.summary()

    def test_summary_deprecations(self):
        diff = ProtocolDiff(deprecated=["old_field"])
        assert "~1 deprecated" in diff.summary()

    def test_not_breaking_when_only_additions(self):
        diff = ProtocolDiff(added=["new_field"])
        assert diff.is_breaking() is False


# ---------------------------------------------------------------------------
# Protocol class structure tests
# ---------------------------------------------------------------------------


class TestPIMProtocols:
    def test_v1_version(self):
        assert PIMConnectorProtocol_v1.VERSION == ProtocolVersion(1, 0)

    def test_v2_version(self):
        assert PIMConnectorProtocol_v2.VERSION == ProtocolVersion(2, 0)

    def test_v2_inherits_v1(self):
        assert issubclass(PIMConnectorProtocol_v2, PIMConnectorProtocol_v1)

    def test_v2_has_more_fields_than_v1(self):
        v1_names = {f.name for f in PIMConnectorProtocol_v1.FIELDS}
        v2_names = {f.name for f in PIMConnectorProtocol_v2.FIELDS}
        assert v2_names > v1_names

    def test_v2_added_fields_carry_version(self):
        added_in_v2 = [
            f for f in PIMConnectorProtocol_v2.FIELDS if f.added_in == ProtocolVersion(2, 0)
        ]
        assert len(added_in_v2) > 0

    def test_invalid_version_type_raises(self):
        with pytest.raises(TypeError, match="ProtocolVersion"):

            class BadProtocol(BaseConnectorProtocol):  # type: ignore[misc]
                VERSION = "1.0"


# ---------------------------------------------------------------------------
# negotiate_version tests
# ---------------------------------------------------------------------------


class TestNegotiateVersion:
    def test_negotiate_v1_returns_v1(self):
        cls = negotiate_version("pim", ProtocolVersion(1, 0))
        assert cls is PIMConnectorProtocol_v1

    def test_negotiate_v2_returns_v2(self):
        cls = negotiate_version("pim", ProtocolVersion(2, 0))
        assert cls is PIMConnectorProtocol_v2

    def test_negotiate_unknown_major_returns_none(self):
        assert negotiate_version("pim", ProtocolVersion(99, 0)) is None

    def test_negotiate_unknown_family_returns_none(self):
        assert negotiate_version("nonexistent_family", ProtocolVersion(1, 0)) is None

    def test_register_and_negotiate_custom_protocol(self):
        class MyProtocol(BaseConnectorProtocol):
            VERSION = ProtocolVersion(3, 0)
            FIELDS: list[FieldSpec] = []

            async def get_product(self, product_id: str) -> dict[str, Any]:
                return {}

        family = "test_custom_family"
        register_protocol(family, MyProtocol)
        result = negotiate_version(family, ProtocolVersion(3, 0))
        assert result is MyProtocol


# ---------------------------------------------------------------------------
# diff_protocols tests
# ---------------------------------------------------------------------------


class TestDiffProtocols:
    def test_v1_to_v2_adds_fields(self):
        diff = diff_protocols(PIMConnectorProtocol_v1, PIMConnectorProtocol_v2)
        assert len(diff.added) > 0
        assert "taxonomy_path" in diff.added
        assert "variants" in diff.added

    def test_v1_to_v2_is_not_breaking(self):
        diff = diff_protocols(PIMConnectorProtocol_v1, PIMConnectorProtocol_v2)
        assert not diff.is_breaking()

    def test_v2_to_v1_is_breaking(self):
        diff = diff_protocols(PIMConnectorProtocol_v2, PIMConnectorProtocol_v1)
        assert diff.is_breaking()
        assert len(diff.removed) > 0

    def test_same_version_no_changes(self):
        diff = diff_protocols(PIMConnectorProtocol_v1, PIMConnectorProtocol_v1)
        assert diff.added == []
        assert diff.removed == []
        assert diff.deprecated == []

    def test_invalid_argument_raises(self):
        with pytest.raises(TypeError, match="BaseConnectorProtocol"):
            diff_protocols(object, PIMConnectorProtocol_v2)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# VersionedAdapter tests
# ---------------------------------------------------------------------------


class TestVersionedAdapter:
    @pytest.fixture
    def connector(self) -> ConcretePIMv2:
        return ConcretePIMv2()

    @pytest.mark.asyncio
    async def test_passthrough_when_versions_match(self, connector):
        adapter = VersionedAdapter(
            connector,
            protocol_class=PIMConnectorProtocol_v2,
            client_version=ProtocolVersion(2, 0),
        )
        product = await adapter.get_product("P-001")
        # v2 fields should be present when client requests v2
        assert "taxonomy_path" in product
        assert "variants" in product

    @pytest.mark.asyncio
    async def test_v2_fields_stripped_for_v1_client(self, connector):
        adapter = VersionedAdapter(
            connector,
            protocol_class=PIMConnectorProtocol_v2,
            client_version=ProtocolVersion(1, 0),
        )
        product = await adapter.get_product("P-001")
        # v2-only fields must be absent
        assert "taxonomy_path" not in product
        assert "variants" not in product
        assert "extended_attrs" not in product
        assert "lifecycle_status" not in product
        # v1 fields must still be present
        assert "product_id" in product
        assert "name" in product

    @pytest.mark.asyncio
    async def test_list_products_applies_mask(self, connector):
        adapter = VersionedAdapter(
            connector,
            protocol_class=PIMConnectorProtocol_v2,
            client_version=ProtocolVersion(1, 0),
        )
        products = await adapter.list_products(limit=2)
        assert len(products) == 2
        for p in products:
            assert "taxonomy_path" not in p
            assert "product_id" in p

    @pytest.mark.asyncio
    async def test_unknown_keys_are_preserved(self, connector):
        """Fields not in any protocol definition (e.g. internal keys) are kept."""
        adapter = VersionedAdapter(
            connector,
            protocol_class=PIMConnectorProtocol_v2,
            client_version=ProtocolVersion(1, 0),
        )

        # Monkey-patch connector to return an internal key
        async def patched_get(product_id: str) -> dict[str, Any]:
            data = await ConcretePIMv2().get_product(product_id)
            data["_internal_trace_id"] = "trace-123"  # not in any protocol FIELDS
            return data

        connector.get_product = patched_get  # type: ignore[method-assign]
        product = await adapter.get_product("P-001")
        assert product["_internal_trace_id"] == "trace-123"

    def test_deprecation_warning_logged_for_old_client(self, connector, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            VersionedAdapter(
                connector,
                protocol_class=PIMConnectorProtocol_v2,
                client_version=ProtocolVersion(1, 0),
            )
        assert any("Consider upgrading" in r.message for r in caplog.records)

    def test_no_warning_when_versions_match(self, connector, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            VersionedAdapter(
                connector,
                protocol_class=PIMConnectorProtocol_v2,
                client_version=ProtocolVersion(2, 0),
            )
        assert not any("Consider upgrading" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_attribute_delegation(self, connector):
        """Non-overridden methods are delegated to the underlying connector."""
        adapter = VersionedAdapter(
            connector,
            protocol_class=PIMConnectorProtocol_v2,
        )
        # search_products is not overridden in VersionedAdapter, delegation expected
        results = await adapter.search_products("headphones")
        assert isinstance(results, list)
