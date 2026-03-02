"""Configuration settings using Pydantic."""

from functools import lru_cache
from typing import List, Literal

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

    # Azure Database for PostgreSQL (CRUD transactional data)
    postgres_host: str = Field(..., description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_database: str = Field(
        default="holiday_peak_crud", description="PostgreSQL database name"
    )
    postgres_auth_mode: Literal["password", "entra"] = Field(
        default="password",
        description="PostgreSQL auth mode: password or Entra token",
    )
    postgres_user: str = Field(..., description="PostgreSQL username")
    postgres_password: str | None = Field(default=None, description="PostgreSQL password")
    postgres_password_secret_name: str = Field(
        default="postgres-admin-password",
        description="Key Vault secret name for PostgreSQL password",
    )
    postgres_ssl: bool = Field(default=True, description="Use SSL for PostgreSQL connection")
    postgres_entra_scope: str = Field(
        default="https://ossrdbms-aad.database.windows.net/.default",
        description="Token scope used for Entra auth with Azure PostgreSQL",
    )
    postgres_min_pool_size: int = Field(default=2, description="Minimum PostgreSQL pool size")
    postgres_max_pool_size: int = Field(default=20, description="Maximum PostgreSQL pool size")

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
        default=None,
        description="Entra ID issuer (e.g., https://login.microsoftonline.com/...)",
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
        default=True,
        description="Enable fallback to basic logic when agents unavailable",
    )
    agent_timeout_seconds: float = Field(
        default=0.5, description="Timeout for agent REST calls (seconds)"
    )
    agent_retry_attempts: int = Field(
        default=2, description="Max retry attempts for agent REST calls"
    )
    agent_circuit_failure_threshold: int = Field(
        default=5, description="Failures before circuit opens for agent REST calls"
    )
    agent_circuit_recovery_seconds: int = Field(
        default=60, description="Circuit breaker recovery timeout (seconds)"
    )

    # APIM gateway for CRUD -> Agent routing
    agent_apim_base_url: str | None = Field(
        default=None,
        description=(
            "APIM base URL used to route CRUD calls to agents "
            "(for example: https://<apim>.azure-api.net)"
        ),
    )

    # Agent REST endpoints (CRUD -> Agent)
    # Ecommerce agents
    product_enrichment_agent_url: str | None = Field(
        default=None, description="Product enrichment agent base URL"
    )
    cart_intelligence_agent_url: str | None = Field(
        default=None, description="Cart intelligence agent base URL"
    )
    checkout_support_agent_url: str | None = Field(
        default=None, description="Checkout support agent base URL"
    )
    catalog_search_agent_url: str | None = Field(
        default=None, description="Catalog search agent base URL"
    )
    order_status_agent_url: str | None = Field(
        default=None, description="Order status agent base URL"
    )
    # Inventory agents
    inventory_health_agent_url: str | None = Field(
        default=None, description="Inventory health agent base URL"
    )
    inventory_reservation_agent_url: str | None = Field(
        default=None, description="Inventory reservation validation agent base URL"
    )
    # Logistics agents
    logistics_eta_agent_url: str | None = Field(
        default=None, description="Logistics ETA computation agent base URL"
    )
    logistics_carrier_agent_url: str | None = Field(
        default=None, description="Logistics carrier selection agent base URL"
    )
    logistics_returns_agent_url: str | None = Field(
        default=None, description="Logistics returns support agent base URL"
    )
    # CRM agents
    crm_profile_agent_url: str | None = Field(
        default=None, description="CRM profile aggregation agent base URL"
    )
    crm_segmentation_agent_url: str | None = Field(
        default=None, description="CRM segmentation/personalization agent base URL"
    )

    # Stripe (loaded from Key Vault)
    stripe_secret_key: str | None = Field(default=None, description="Stripe secret key")
    stripe_webhook_secret: str | None = Field(default=None, description="Stripe webhook secret")

    # ACP Merchant Settings
    merchant_id: str = Field(
        default="holiday-peak-hub",
        description="Merchant identifier for ACP checkout and payments",
    )

    # SendGrid (optional, for email notifications)
    sendgrid_api_key: str | None = Field(default=None, description="SendGrid API key")

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        protocol = "rediss" if self.redis_ssl else "redis"
        return f"{protocol}://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def postgres_dsn(self) -> str:
        """Construct PostgreSQL DSN for asyncpg."""
        if self.postgres_auth_mode == "entra":
            raise ValueError(
                "PostgreSQL DSN is unavailable when POSTGRES_AUTH_MODE=entra. "
                "Use token-based connection parameters instead."
            )
        if not self.postgres_password:
            raise ValueError(
                "PostgreSQL password is not configured. "
                "Set POSTGRES_PASSWORD or configure Key Vault secret loading."
            )
        sslmode = "require" if self.postgres_ssl else "disable"
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_database}?sslmode={sslmode}"
        )

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
