"""Unit tests for CRUD demo seed cleanup logic."""

# pylint: disable=protected-access

import pytest
from crud_service.scripts import seed_demo_data


class _StubConnection:
    def __init__(self, statuses: list[str]) -> None:
        self._statuses = statuses
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *params: object) -> str:
        self.calls.append((query, params))
        return self._statuses.pop(0)


def test_affected_row_count_parses_delete_status() -> None:
    assert seed_demo_data._affected_row_count("DELETE 14") == 14
    assert seed_demo_data._affected_row_count("UPDATE 3") == 3
    assert seed_demo_data._affected_row_count("CREATE TABLE") == 0
    assert seed_demo_data._affected_row_count(None) == 0


@pytest.mark.asyncio
async def test_purge_legacy_seed_catalog_targets_fake_and_non_curated_seeded_rows() -> None:
    conn = _StubConnection(["DELETE 7", "DELETE 3"])

    deleted_products, deleted_categories = await seed_demo_data._purge_legacy_seed_catalog(conn)

    assert deleted_products == 7
    assert deleted_categories == 3
    assert len(conn.calls) == 2
    assert "DELETE FROM products" in conn.calls[0][0]
    assert "DELETE FROM categories" in conn.calls[1][0]

    curated_ids = conn.calls[0][1][0]
    fake_names = conn.calls[0][1][1]
    assert "cat-electronics" in curated_ids
    assert "cat-furniture" in curated_ids
    assert "Purpose Brother" in fake_names
    assert "Offer Kind" in fake_names


@pytest.mark.asyncio
async def test_purge_legacy_seed_catalog_is_idempotent_when_nothing_matches() -> None:
    conn = _StubConnection(["DELETE 0", "DELETE 0"])

    deleted_products, deleted_categories = await seed_demo_data._purge_legacy_seed_catalog(conn)

    assert deleted_products == 0
    assert deleted_categories == 0
