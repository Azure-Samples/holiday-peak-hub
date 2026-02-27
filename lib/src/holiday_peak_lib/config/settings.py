"""Configuration models."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    redis_url: str | None = None
    cosmos_account_uri: str | None = None
    cosmos_database: str | None = None
    cosmos_container: str | None = None
    blob_account_url: str | None = None
    blob_container: str | None = None


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

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
    model_config = SettingsConfigDict(env_file=".env")

    postgres_dsn: str
