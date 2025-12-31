"""Configuration models."""
from pydantic import BaseSettings, Field


class MemorySettings(BaseSettings):
    redis_url: str = Field(..., env="REDIS_URL")
    cosmos_account_uri: str = Field(..., env="COSMOS_ACCOUNT_URI")
    cosmos_database: str = Field(..., env="COSMOS_DATABASE")
    cosmos_container: str = Field(..., env="COSMOS_CONTAINER")
    blob_account_url: str = Field(..., env="BLOB_ACCOUNT_URL")
    blob_container: str = Field(..., env="BLOB_CONTAINER")


class ServiceSettings(BaseSettings):
    service_name: str = Field(..., env="SERVICE_NAME")
    ai_search_endpoint: str = Field(..., env="AI_SEARCH_ENDPOINT")
    ai_search_index: str = Field(..., env="AI_SEARCH_INDEX")
    ai_search_key: str = Field(..., env="AI_SEARCH_KEY")
    event_hub_namespace: str = Field(..., env="EVENT_HUB_NAMESPACE")
    event_hub_name: str = Field(..., env="EVENT_HUB_NAME")
    monitor_connection_string: str | None = Field(default=None, env="AZURE_MONITOR_CONNECTION_STRING")


class PostgresSettings(BaseSettings):
    postgres_dsn: str = Field(..., env="POSTGRES_DSN")
