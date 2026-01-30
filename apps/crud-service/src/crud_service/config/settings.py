"""Configuration settings using Pydantic."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    service_name: str = Field(default="crud-service", description="Service name")
    environment: str = Field(default="dev", description="Environment (dev, staging, prod)")
    log_level: str = Field(default="INFO", description="Logging level")

    # Azure Cosmos DB (use Managed Identity, no connection string)
    cosmos_account_uri: str = Field(
        ..., description="Cosmos DB account URI (e.g., https://xxx.documents.azure.com:443/)"
    )
    cosmos_database: str = Field(default="holiday-peak-db", description="Cosmos DB database name")

    # Azure Event Hubs (use Managed Identity, no connection string)
    event_hub_namespace: str = Field(
        ..., description="Event Hubs namespace (e.g., xxx.servicebus.windows.net)"
    )

    # Azure Key Vault (use Managed Identity)
    key_vault_uri: str = Field(..., description="Key Vault URI")

    # Redis (for caching)
    redis_host: str = Field(..., description="Redis host")
    redis_port: int = Field(default=6380, description="Redis port (SSL)")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_ssl: bool = Field(default=True, description="Use SSL for Redis")

    # Authentication (Microsoft Entra ID) - secrets loaded from Key Vault
    entra_tenant_id: str | None = Field(default=None, description="Entra ID tenant ID")
    entra_client_id: str | None = Field(default=None, description="Entra ID client ID")
    entra_client_secret: str | None = Field(default=None, description="Entra ID client secret")
    entra_issuer: str | None = Field(
        default=None, description="Entra ID issuer (e.g., https://login.microsoftonline.com/...)"
    )

    # CORS
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",  # Local Next.js dev
            "https://*.azurestaticapps.net",  # Azure Static Web Apps
            "https://holidaypeakhub.com",  # Production domain
            "https://www.holidaypeakhub.com",
        ],
        description="Allowed CORS origins",
    )

    # Application Insights (optional)
    app_insights_connection_string: str | None = Field(
        default=None, description="Application Insights connection string"
    )

    # Feature Flags
    enable_agent_fallback: bool = Field(
        default=True, description="Enable fallback to basic logic when agents unavailable"
    )
    agent_timeout_seconds: float = Field(
        default=3.0, description="Timeout for agent MCP calls (seconds)"
    )

    # Stripe (loaded from Key Vault)
    stripe_secret_key: str | None = Field(default=None, description="Stripe secret key")
    stripe_webhook_secret: str | None = Field(default=None, description="Stripe webhook secret")

    # SendGrid (optional, for email notifications)
    sendgrid_api_key: str | None = Field(default=None, description="SendGrid API key")

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        protocol = "rediss" if self.redis_ssl else "redis"
        return f"{protocol}://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "prod"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "dev"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
