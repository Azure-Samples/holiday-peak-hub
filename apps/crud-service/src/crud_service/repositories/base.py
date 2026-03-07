"""Base repository for PostgreSQL operations using asyncpg."""

import json
import logging
import re
from typing import Any, Generic, TypeVar

import asyncpg
from azure.identity.aio import DefaultAzureCredential
from crud_service.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository for PostgreSQL operations.

    Uses asyncpg connection pooling and JSONB-backed tables.
    Preserves existing repository API while migrating storage from Cosmos DB.
    """

    _pool: asyncpg.Pool | None = None
    _credential: DefaultAzureCredential | None = None
    _initialized_tables: set[str] = set()
    _pool_init_error: str | None = None

    def __init__(self, container_name: str):
        """
        Initialize repository.

        Args:
            container_name: Logical repository/table name
        """
        self.container_name = container_name
        self.table_name = container_name

    @classmethod
    async def initialize_pool(cls):
        """Initialize shared PostgreSQL connection pool."""
        if cls._pool is None:
            try:
                if settings.postgres_auth_mode == "entra":
                    cls._pool = await asyncpg.create_pool(
                        host=settings.postgres_host,
                        port=settings.postgres_port,
                        user=settings.postgres_user,
                        database=settings.postgres_database,
                        ssl="require" if settings.postgres_ssl else None,
                        min_size=settings.postgres_min_pool_size,
                        max_size=settings.postgres_max_pool_size,
                        connect=cls._connect_with_entra_token,
                    )
                else:
                    cls._pool = await asyncpg.create_pool(
                        dsn=settings.postgres_dsn,
                        min_size=settings.postgres_min_pool_size,
                        max_size=settings.postgres_max_pool_size,
                    )
                cls._pool_init_error = None
            except Exception as exc:
                cls._pool_init_error = f"{type(exc).__name__}: {exc}"
                cls._pool = None
                raise

    @classmethod
    async def check_pool_health(cls) -> tuple[str, str]:
        """Return (status, detail) for PostgreSQL pool readiness."""
        if cls._pool_init_error and cls._pool is None:
            return "unhealthy", cls._pool_init_error

        try:
            if cls._pool is None:
                await cls.initialize_pool()
            if cls._pool is None:
                return "unhealthy", "Pool unavailable"
            async with cls._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return "healthy", "query ok"
        except Exception as exc:
            cls._pool_init_error = f"{type(exc).__name__}: {exc}"
            return "unhealthy", cls._pool_init_error

    @classmethod
    def _get_credential(cls) -> DefaultAzureCredential:
        if cls._credential is None:
            cls._credential = DefaultAzureCredential()
        return cls._credential

    @classmethod
    async def _connect_with_entra_token(cls, *args, **kwargs):
        token = await cls._get_credential().get_token(settings.postgres_entra_scope)
        kwargs["password"] = token.token
        return await asyncpg.connect(*args, **kwargs)

    @classmethod
    async def close_pool(cls):
        """Close shared PostgreSQL connection pool."""
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None
            cls._initialized_tables = set()
        cls._pool_init_error = None
        if cls._credential is not None:
            await cls._credential.close()
            cls._credential = None

    async def _get_pool(self) -> asyncpg.Pool:
        """Get initialized PostgreSQL pool."""
        try:
            await self.initialize_pool()
        except Exception as exc:
            raise RuntimeError("PostgreSQL connection pool is unavailable") from exc
        if self._pool is None:
            raise RuntimeError("PostgreSQL connection pool is unavailable")
        return self._pool

    @staticmethod
    def _decode_row_data(raw_data: Any) -> dict[str, Any] | None:
        """Decode a row payload into a dict; malformed rows are skipped."""
        try:
            if isinstance(raw_data, str):
                decoded = json.loads(raw_data)
                if isinstance(decoded, dict):
                    return decoded
                return None
            if isinstance(raw_data, dict):
                return dict(raw_data)
            return dict(raw_data)
        except Exception as exc:
            logger.warning("Skipping malformed row payload: %s", exc)
            return None

    @staticmethod
    def _extract_partition_key(item: dict[str, Any]) -> str:
        """Extract best-effort partition key from item for compatibility."""
        for field_name in (
            "user_id",
            "order_id",
            "product_id",
            "category_slug",
            "entity_type",
            "agent_id",
            "session_id",
            "id",
        ):
            value = item.get(field_name)
            if value is not None:
                return str(value)
        return str(item.get("id", ""))

    async def _ensure_table(self):
        """Ensure JSONB table exists for this repository."""
        if self.table_name in self._initialized_tables:
            return

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    partition_key TEXT,
                    data JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """)
            await conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_partition_key ON {self.table_name}(partition_key)"
            )
            await conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_data_gin ON {self.table_name} USING GIN (data)"
            )

        self._initialized_tables.add(self.table_name)

    async def create(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new item.

        Args:
            item: Item to create (must include 'id' and partition key)

        Returns:
            Created item with metadata
        """
        await self._ensure_table()
        pool = await self._get_pool()
        partition_key = self._extract_partition_key(item)

        async with pool.acquire() as conn:
            await conn.execute(
                f"INSERT INTO {self.table_name} (id, partition_key, data) VALUES ($1, $2, $3::jsonb)",
                item["id"],
                partition_key,
                json.dumps(item),
            )

        return item

    async def get_by_id(
        self, item_id: str, partition_key: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get item by ID.

        Args:
            item_id: Item ID
            partition_key: Partition key value (optional if same as ID)

        Returns:
            Item or None if not found
        """
        await self._ensure_table()
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            if partition_key:
                row = await conn.fetchrow(
                    f"SELECT data FROM {self.table_name} WHERE id = $1 AND partition_key = $2",
                    item_id,
                    partition_key,
                )
            else:
                row = await conn.fetchrow(
                    f"SELECT data FROM {self.table_name} WHERE id = $1",
                    item_id,
                )

        if row:
            return self._decode_row_data(row["data"])

        logger.warning("Item not found: %s", item_id)
        return None

    async def update(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Update an existing item (upsert).

        Args:
            item: Item to update (must include 'id' and partition key)

        Returns:
            Updated item with metadata
        """
        await self._ensure_table()
        pool = await self._get_pool()
        partition_key = self._extract_partition_key(item)

        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} (id, partition_key, data, created_at, updated_at)
                VALUES ($1, $2, $3::jsonb, NOW(), NOW())
                ON CONFLICT (id)
                DO UPDATE SET
                    partition_key = EXCLUDED.partition_key,
                    data = EXCLUDED.data,
                    updated_at = NOW()
                """,
                item["id"],
                partition_key,
                json.dumps(item),
            )

        return item

    async def delete(self, item_id: str, partition_key: str | None = None) -> None:
        """
        Delete an item.

        Args:
            item_id: Item ID
            partition_key: Partition key value (optional if same as ID)
        """
        await self._ensure_table()
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            if partition_key:
                await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE id = $1 AND partition_key = $2",
                    item_id,
                    partition_key,
                )
            else:
                await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE id = $1",
                    item_id,
                )

    async def query(
        self,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
        partition_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            parameters: Query parameters (e.g., [{"name": "@id", "value": "123"}])
            partition_key: Partition key for query (enables single-partition query)

        Returns:
            List of items matching query
        """
        await self._ensure_table()
        pool = await self._get_pool()

        parameter_map = {p["name"]: p["value"] for p in (parameters or [])}

        async with pool.acquire() as conn:
            if partition_key:
                rows = await conn.fetch(
                    f"SELECT data FROM {self.table_name} WHERE partition_key = $1",
                    partition_key,
                )
            else:
                rows = await conn.fetch(f"SELECT data FROM {self.table_name}")

        items: list[dict[str, Any]] = []
        for row in rows:
            decoded = self._decode_row_data(row["data"])
            if decoded is not None:
                items.append(decoded)

        where_clause = ""
        where_match = re.search(r"WHERE\s+(.*?)\s*(ORDER BY|OFFSET|LIMIT|$)", query, re.IGNORECASE)
        if where_match:
            where_clause = where_match.group(1).strip()

        if where_clause:
            items = [
                item for item in items if self._matches_where(item, where_clause, parameter_map)
            ]

        order_match = re.search(r"ORDER BY\s+c\.(\w+)\s+(ASC|DESC)", query, re.IGNORECASE)
        if order_match:
            order_field = order_match.group(1)
            reverse = order_match.group(2).upper() == "DESC"
            items = sorted(items, key=lambda item: item.get(order_field, ""), reverse=reverse)

        limit_match = re.search(r"LIMIT\s+(@\w+|\d+)", query, re.IGNORECASE)
        if limit_match:
            limit_token = limit_match.group(1)
            if limit_token.startswith("@"):
                limit_value = int(parameter_map.get(limit_token, len(items)))
            else:
                limit_value = int(limit_token)
            items = items[:limit_value]

        return items

    @staticmethod
    def _matches_where(item: dict[str, Any], clause: str, params: dict[str, Any]) -> bool:
        """Evaluate limited Cosmos-style WHERE clauses against JSON data."""
        if " OR " in clause.upper():
            parts = re.split(r"\s+OR\s+", clause, flags=re.IGNORECASE)
            return any(BaseRepository._matches_where(item, part, params) for part in parts)

        if " AND " in clause.upper():
            parts = re.split(r"\s+AND\s+", clause, flags=re.IGNORECASE)
            return all(BaseRepository._matches_where(item, part, params) for part in parts)

        contains_match = re.match(
            r"CONTAINS\(LOWER\(c\.(\w+)\),\s*LOWER\((@\w+)\)\)",
            clause,
            re.IGNORECASE,
        )
        if contains_match:
            field_name, param_name = contains_match.groups()
            value = str(item.get(field_name, "")).lower()
            term = str(params.get(param_name, "")).lower()
            return term in value

        not_defined_match = re.match(r"NOT IS_DEFINED\(c\.(\w+)\)", clause, re.IGNORECASE)
        if not_defined_match:
            field_name = not_defined_match.group(1)
            return field_name not in item

        null_match = re.match(r"c\.(\w+)\s*=\s*null", clause, re.IGNORECASE)
        if null_match:
            field_name = null_match.group(1)
            return item.get(field_name) is None

        parameter_match = re.match(r"c\.(\w+)\s*=\s*(@\w+)", clause, re.IGNORECASE)
        if parameter_match:
            field_name, param_name = parameter_match.groups()
            return item.get(field_name) == params.get(param_name)

        literal_match = re.match(r"c\.(\w+)\s*=\s*'([^']*)'", clause, re.IGNORECASE)
        if literal_match:
            field_name, literal_value = literal_match.groups()
            return str(item.get(field_name)) == literal_value

        return True
