"""Tests for Fabric-to-AI-Search ingestion support."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from search_enrichment_agent.fabric_search_ingestion import (
    AISearchResourceSettings,
    FabricSearchIngestionSettings,
    OneLakeFilesMetadataProvider,
    SearchResourceBuilder,
    SearchResourceProvisioner,
    SourceColumn,
    SourceMetadata,
    build_mapping_plan,
    register_fabric_search_ingestion_tools,
)


def _env(overrides: dict[str, str] | None = None) -> dict[str, str]:
    base = {
        "FABRIC_SOURCE_KIND": "sql",
        "FABRIC_SQL_ENDPOINT": "fabric-sql.database.fabric.microsoft.com",
        "FABRIC_SQL_DATABASE": "RetailWarehouse",
        "FABRIC_SQL_SCHEMA": "dbo",
        "FABRIC_SQL_TABLE": "ProductsForSearch",
        "FABRIC_INCREMENTAL_COLUMN": "modified_at",
        "FABRIC_SOFT_DELETE_COLUMN": "is_deleted",
        "FABRIC_SOFT_DELETE_MARKER": "true",
        "FABRIC_APPROVAL_COLUMN": "approval_status",
        "FABRIC_APPROVAL_ACCEPTED_VALUES": "approved,published",
        "FABRIC_SAMPLE_ROWS": "7",
        "AI_SEARCH_ENDPOINT": "https://catalog-search.search.windows.net",
        "AI_SEARCH_AUTH_MODE": "api_key",
        "AI_SEARCH_ADMIN_KEY": "test-key",
        "AI_SEARCH_INDEX": "catalog-products",
        "AI_SEARCH_VECTOR_INDEX": "catalog-products",
        "AI_SEARCH_VECTOR_FIELD": "content_vector",
        "AI_SEARCH_DATASOURCE_NAME": "fabric-products-ds",
        "AI_SEARCH_SKILLSET_NAME": "fabric-products-skillset",
        "AI_SEARCH_INDEXER_NAME": "fabric-products-indexer",
        "AI_SEARCH_SEMANTIC_CONFIG_NAME": "catalog-semantic",
        "EMBEDDING_RESOURCE_URI": "https://aoai.openai.azure.com/",
        "EMBEDDING_DEPLOYMENT_NAME": "text-embedding-3-small",
        "EMBEDDING_MODEL_NAME": "text-embedding-3-small",
        "EMBEDDING_DIMENSIONS": "1536",
    }
    if overrides:
        base.update(overrides)
    return base


def _sample_metadata() -> SourceMetadata:
    return SourceMetadata(
        source_kind="sql",
        source_name="RetailWarehouse.dbo.ProductsForSearch",
        columns=(
            SourceColumn("product_id", "nvarchar", False),
            SourceColumn("title", "nvarchar"),
            SourceColumn("long_description", "nvarchar"),
            SourceColumn("brand_name", "nvarchar"),
            SourceColumn("category_name", "nvarchar"),
            SourceColumn("list_price", "decimal", sample_values=("19.95", "24.00")),
            SourceColumn("currency_code", "nvarchar", sample_values=("USD",)),
            SourceColumn("stock_status", "nvarchar", sample_values=("in_stock",)),
            SourceColumn("approval_status", "nvarchar", sample_values=("approved",)),
            SourceColumn("modified_at", "datetime2"),
            SourceColumn("is_deleted", "bit"),
        ),
        sample_rows=(
            {
                "product_id": "SKU-1",
                "title": "Trail Shoe",
                "long_description": "Daily trail running shoe",
                "approval_status": "approved",
            },
        ),
    )


def _resource_payloads() -> tuple[SearchResourceBuilder, Any]:
    settings = FabricSearchIngestionSettings.from_env(_env())
    plan = build_mapping_plan(_sample_metadata(), settings)
    builder = SearchResourceBuilder(settings)
    return builder, builder.build(plan)


def test_env_loading_supports_fabric_and_search_settings() -> None:
    settings = FabricSearchIngestionSettings.from_env(
        _env({"FABRIC_SAMPLE_ROWS": "999", "EMBEDDING_DIMENSIONS": "3072"})
    )

    assert settings.fabric.source_kind == "sql"
    assert settings.fabric.sql_schema == "dbo"
    assert settings.fabric.sample_rows == 50
    assert settings.fabric.approval_accepted_values == ("approved", "published")
    assert settings.search.endpoint == "https://catalog-search.search.windows.net"
    assert settings.search.index_name == "catalog-products"
    assert settings.search.vector_field == "content_vector"
    assert settings.search.embedding_dimensions == 3072
    assert settings.search.api_version == "2026-04-01"


def test_build_mapping_plan_uses_synonyms_and_governance_signal() -> None:
    settings = FabricSearchIngestionSettings.from_env(_env())

    plan = build_mapping_plan(_sample_metadata(), settings)

    mappings = {mapping.target_field: mapping for mapping in plan.mappings}
    assert mappings["id"].source_field == "product_id"
    assert mappings["sku"].source_field == "product_id"
    assert mappings["name"].source_field == "title"
    assert mappings["description"].source_field == "long_description"
    assert mappings["brand"].source_field == "brand_name"
    assert mappings["category"].source_field == "category_name"
    assert mappings["content"].transform.startswith("concat_non_empty")
    assert mappings["price"].source_field == "list_price"
    assert mappings["currency"].source_field == "currency_code"
    assert plan.governance.status == "configured"
    assert plan.governance.column == "approval_status"
    assert plan.governance.to_dict()["truth_lifecycle_state_mutated"] is False


@pytest.mark.asyncio
async def test_onelake_tables_path_is_rejected() -> None:
    settings = FabricSearchIngestionSettings.from_env(
        _env(
            {
                "FABRIC_SOURCE_KIND": "onelake_files",
                "FABRIC_WORKSPACE_ID": "workspace-guid",
                "FABRIC_ONELAKE_LAKEHOUSE_ID": "lakehouse-guid",
                "FABRIC_ONELAKE_FILES_PATH": "Tables/Products",
            }
        )
    )
    provider = OneLakeFilesMetadataProvider(settings.fabric)

    with pytest.raises(Exception) as exc_info:
        await provider.discover()

    assert "OneLake AI Search indexers support lakehouse Files" in str(exc_info.value)


def test_build_search_resource_payloads_match_catalog_index_shape() -> None:
    _, payloads = _resource_payloads()

    index = payloads.index
    fields = {field["name"]: field for field in index["fields"]}
    assert index["name"] == "catalog-products"
    assert fields["id"]["key"] is True
    assert fields["content"]["searchable"] is True
    assert fields["content_vector"]["type"] == "Collection(Edm.Single)"
    assert fields["content_vector"]["dimensions"] == 1536
    assert index["vectorSearch"]["algorithms"][0]["hnswParameters"]["metric"] == "cosine"
    assert index["semantic"]["configurations"][0]["name"] == "catalog-semantic"

    skillset = payloads.skillset
    assert len(skillset["skills"]) == 1
    embedding_skill = skillset["skills"][0]
    assert embedding_skill["@odata.type"] == "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill"
    assert embedding_skill["context"] == "/document"
    assert embedding_skill["inputs"] == [{"name": "text", "source": "/document/content"}]
    assert embedding_skill["outputs"] == [{"name": "embedding", "targetName": "embedding"}]
    assert embedding_skill["dimensions"] == fields["content_vector"]["dimensions"]

    data_source = payloads.data_source
    assert data_source["type"] == "azuresql"
    assert data_source["dataChangeDetectionPolicy"]["highWaterMarkColumnName"] == "modified_at"
    assert data_source["dataDeletionDetectionPolicy"]["softDeleteColumnName"] == "is_deleted"

    indexer = payloads.indexer
    assert indexer["targetIndexName"] == "catalog-products"
    assert {mapping["targetFieldName"] for mapping in indexer["fieldMappings"]} >= {
        "id",
        "name",
        "content",
    }
    assert indexer["outputFieldMappings"] == [
        {"sourceFieldName": "/document/embedding/*", "targetFieldName": "content_vector"}
    ]


@pytest.mark.asyncio
async def test_provisioning_client_puts_resources_and_runs_indexer() -> None:
    _, payloads = _resource_payloads()
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        status_code = 202 if request.url.path.endswith("/search.run") else 201
        return httpx.Response(status_code, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = SearchResourceProvisioner(
        settings=payloads.mapping_plan and FabricSearchIngestionSettings.from_env(_env()).search,
        transport=transport,
    )

    provision = await client.provision(payloads)
    run = await client.run_indexer()

    assert provision["status"] == "ok"
    assert run["status"] == "accepted"
    assert [request.method for request in requests] == ["PUT", "PUT", "PUT", "PUT", "POST"]
    paths = [request.url.path for request in requests]
    assert paths[:4] == [
        "/indexes('catalog-products')",
        "/skillsets('fabric-products-skillset')",
        "/datasources('fabric-products-ds')",
        "/indexers('fabric-products-indexer')",
    ]
    assert paths[4] == "/indexers('fabric-products-indexer')/search.run"
    assert all("api-version=2026-04-01" in str(request.url) for request in requests)
    assert requests[0].headers["api-key"] == "test-key"


@pytest.mark.asyncio
async def test_mcp_tools_register_and_execute_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _env().items():
        monkeypatch.setenv(key, value)

    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        status_code = 202 if request.url.path.endswith("/search.run") else 201
        return httpx.Response(status_code, json={"ok": True})

    transport = httpx.MockTransport(handler)

    def provisioner_factory(settings: AISearchResourceSettings) -> SearchResourceProvisioner:
        return SearchResourceProvisioner(settings=settings, transport=transport)

    mcp = type("MCP", (), {"tools": {}})()

    def add_tool(path, handler_fn):  # noqa: ANN001
        mcp.tools[path] = handler_fn

    mcp.add_tool = add_tool
    register_fabric_search_ingestion_tools(mcp, provisioner_factory=provisioner_factory)

    payload = {"source_metadata": _sample_metadata().to_dict()}
    discover = await mcp.tools["/fabric-search-ingestion/discover_source"](payload)
    mapping = await mcp.tools["/fabric-search-ingestion/build_mapping_plan"](payload)
    resources = await mcp.tools["/fabric-search-ingestion/build_search_resources"](payload)
    provision = await mcp.tools["/fabric-search-ingestion/provision_search_resources"](payload)
    run = await mcp.tools["/fabric-search-ingestion/run_indexer"]({})

    assert discover["status"] == "ok"
    assert mapping["status"] == "ok"
    assert mapping["governance"]["status"] == "configured"
    assert resources["status"] == "ok"
    assert resources["resources"]["data_source"]["credentials"]["connectionString"] == "<redacted>"
    assert provision["status"] == "ok"
    assert run["status"] == "accepted"
    assert len(requests) == 5
