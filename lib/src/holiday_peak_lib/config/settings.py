"""Configuration models."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    redis_url: str
    cosmos_account_uri: str
    cosmos_database: str
    cosmos_container: str
    blob_account_url: str
    blob_container: str


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
