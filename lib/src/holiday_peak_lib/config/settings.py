"""Configuration models."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str | None = None
    redis_host: str | None = None
    redis_password: str | None = None
    redis_password_secret_name: str = "redis-primary-key"
    key_vault_uri: str | None = None
    cosmos_account_uri: str | None = None
    cosmos_database: str | None = None
    cosmos_container: str | None = None
    blob_account_url: str | None = None
    blob_container: str | None = None

    def resolve_redis_url(self, password: str | None = None) -> str | None:
        """Return a fully-formed Redis URL.

        Priority:
        1. ``redis_url`` if already set (passthrough).
        2. Constructed from ``redis_host`` + optional *password* arg or
           ``redis_password`` env var.
        """
        if self.redis_url:
            return self.redis_url
        host = self.redis_host
        if not host:
            return None
        if not host.endswith(".redis.cache.windows.net"):
            host = f"{host}.redis.cache.windows.net"
        pw = password or self.redis_password
        auth = f":{pw}@" if pw else ""
        return f"rediss://{auth}{host}:6380/0"


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str
    ai_search_endpoint: str
    ai_search_index: str
    ai_search_key: str
    event_hub_namespace: str
    event_hub_name: str
    azure_monitor_connection_string: str | None = None

    @property
    def monitor_connection_string(self) -> str | None:
        return self.azure_monitor_connection_string


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_dsn: str


class TruthLayerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRUTH_", env_file=".env", extra="ignore")

    # Cosmos DB containers
    cosmos_products_container: str = "products"
    cosmos_attributes_truth_container: str = "attributes_truth"
    cosmos_attributes_proposed_container: str = "attributes_proposed"
    cosmos_schemas_container: str = "schemas"
    cosmos_mappings_container: str = "mappings"
    cosmos_audit_container: str = "audit"
    cosmos_config_container: str = "config"
    cosmos_relationships_container: str = "relationships"
    cosmos_completeness_container: str = "completeness"

    # Event Hub topics
    eventhub_enrichment_jobs: str = "enrichment-jobs"
    eventhub_completeness_jobs: str = "completeness-jobs"
    eventhub_export_jobs: str = "export-jobs"
    eventhub_hitl_jobs: str = "hitl-jobs"
    eventhub_ingestion_notifications: str = "ingestion-notifications"

    # Feature toggles
    enrichment_enabled: bool = True
    auto_approve_enabled: bool = True
    auto_approve_threshold: float = 0.85
    writeback_enabled: bool = False
    evidence_extraction_enabled: bool = False

    # Operational
    max_enrichment_retries: int = 3
    completeness_cache_ttl_seconds: int = 300
