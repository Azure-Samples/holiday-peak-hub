# ADR-024: Connector Registry Pattern

**Status**: Accepted  
**Date**: 2026-03  
**Deciders**: Architecture Team

## Context

The accelerator connects to diverse enterprise systems across retail domains:

| Domain | Systems |
|--------|---------|
| Inventory & SCM | Oracle Fusion, SAP S/4HANA, Manhattan WMS |
| CRM & Loyalty | Salesforce, Microsoft Dynamics 365, SAP CRM |
| PIM | Akeneo, Salsify, inRiver |
| Pricing | SAP CPQ, Vendavo, Pricefx |

Each connector requires:
- Different authentication mechanisms (OAuth2, API keys, certificates)
- Unique configuration parameters
- Resilience settings tuned to vendor SLAs
- Feature flags for gradual rollout

Without a centralized registry, connector instantiation becomes scattered, credentials are duplicated, and adding new connectors requires code changes across multiple services.

Key questions addressed:
- How do services discover available connectors?
- How are credentials managed securely?
- How do we swap implementations without code changes?
- How do we test with mock connectors?

## Decision

**Implement a Connector Registry using the Factory pattern with environment-driven configuration.**

### Registry Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ConnectorRegistry                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ InventorySCM│  │  CRMLoyalty │  │     PIM     │         │
│  │   Factory   │  │   Factory   │  │   Factory   │   ...   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│    ┌────┴────┐      ┌────┴────┐      ┌────┴────┐           │
│    │ Oracle  │      │Salesforce│     │ Akeneo  │           │
│    │  SAP    │      │Dynamics  │     │ Salsify │           │
│    │Manhattan│      │ SAP CRM  │     │ inRiver │           │
│    └─────────┘      └──────────┘     └─────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### Factory Implementation

```python
from holiday_peak_lib.connectors import ConnectorRegistry, ConnectorType
from holiday_peak_lib.connectors.inventory_scm import (
    OracleFusionConnector,
    SAPConnector, 
    ManhattanConnector,
)

class InventorySCMFactory:
    """Factory for Inventory & SCM connectors."""
    
    _registry: dict[str, type] = {
        "oracle-fusion": OracleFusionConnector,
        "sap-s4hana": SAPConnector,
        "manhattan-wms": ManhattanConnector,
    }
    
    @classmethod
    def create(cls, connector_name: str, config: ConnectorConfig) -> BaseConnector:
        """Create connector instance by name."""
        connector_class = cls._registry.get(connector_name)
        if not connector_class:
            raise UnknownConnectorError(f"Unknown inventory connector: {connector_name}")
        return connector_class(config)
    
    @classmethod
    def register(cls, name: str, connector_class: type):
        """Register a custom connector (for extensions)."""
        cls._registry[name] = connector_class
    
    @classmethod
    def available(cls) -> list[str]:
        """List available connectors."""
        return list(cls._registry.keys())
```

### Environment-Driven Configuration

Connectors are configured via environment variables with a consistent naming convention:

```bash
# Pattern: CONNECTOR_{DOMAIN}_{SYSTEM}_{SETTING}
CONNECTOR_INVENTORY_PROVIDER=oracle-fusion
CONNECTOR_INVENTORY_ORACLE_ENDPOINT=https://xxx.oraclecloud.com
CONNECTOR_INVENTORY_ORACLE_CLIENT_ID=akeneo-client
CONNECTOR_INVENTORY_ORACLE_CLIENT_SECRET=@Microsoft.KeyVault(SecretUri=...)

CONNECTOR_CRM_PROVIDER=salesforce
CONNECTOR_CRM_SALESFORCE_INSTANCE_URL=https://xxx.salesforce.com
CONNECTOR_CRM_SALESFORCE_CLIENT_ID=sf-client
CONNECTOR_CRM_SALESFORCE_CLIENT_SECRET=@Microsoft.KeyVault(SecretUri=...)

CONNECTOR_PIM_PROVIDER=akeneo
CONNECTOR_PIM_AKENEO_BASE_URL=https://xxx.cloud.akeneo.com
CONNECTOR_PIM_AKENEO_CLIENT_ID=pim-client
CONNECTOR_PIM_AKENEO_CLIENT_SECRET=@Microsoft.KeyVault(SecretUri=...)
```

### Credential Management

Credentials follow a hierarchy with Azure Key Vault integration:

```python
from holiday_peak_lib.connectors import CredentialProvider

class ConnectorConfig:
    """Configuration with secure credential resolution."""
    
    def __init__(self, env_prefix: str):
        self.endpoint = os.getenv(f"{env_prefix}_ENDPOINT")
        self.client_id = os.getenv(f"{env_prefix}_CLIENT_ID")
        self._client_secret_ref = os.getenv(f"{env_prefix}_CLIENT_SECRET")
    
    @property
    async def client_secret(self) -> str:
        """Resolve secret from Key Vault or environment."""
        if self._client_secret_ref.startswith("@Microsoft.KeyVault"):
            return await CredentialProvider.resolve_keyvault(self._client_secret_ref)
        return self._client_secret_ref
```

**Credential Resolution Order**:
1. Azure Key Vault reference (production)
2. Managed Identity token (Azure services)
3. Environment variable (development)
4. DefaultAzureCredential fallback

### Mock Connector Support

For testing and development, mock connectors are registered:

```python
# conftest.py or test setup
from holiday_peak_lib.connectors.inventory_scm import MockInventoryConnector

@pytest.fixture
def mock_inventory_connector():
    # Register mock for tests
    InventorySCMFactory.register("mock", MockInventoryConnector)
    
    # Set environment to use mock
    os.environ["CONNECTOR_INVENTORY_PROVIDER"] = "mock"
    
    yield
    
    # Cleanup
    os.environ["CONNECTOR_INVENTORY_PROVIDER"] = "oracle-fusion"
```

### Service Integration

Services request connectors via the registry:

```python
from holiday_peak_lib.connectors import ConnectorRegistry

class InventoryAdapter:
    def __init__(self):
        # Get connector based on CONNECTOR_INVENTORY_PROVIDER env var
        self.connector = ConnectorRegistry.get_inventory_connector()
    
    async def check_availability(self, sku: str) -> StockLevel:
        return await self.connector.fetch_inventory(sku)
```

### Connector Interface Contract

All connectors implement domain-specific interfaces:

```python
from abc import ABC, abstractmethod

class InventorySCMConnector(ABC):
    """Interface for Inventory & SCM connectors."""
    
    @abstractmethod
    async def fetch_inventory(self, sku: str) -> InventoryData:
        """Get current stock level for SKU."""
        pass
    
    @abstractmethod
    async def reserve_stock(self, sku: str, quantity: int, order_id: str) -> Reservation:
        """Create stock reservation."""
        pass
    
    @abstractmethod
    async def release_reservation(self, reservation_id: str) -> bool:
        """Release existing reservation."""
        pass

class CRMLoyaltyConnector(ABC):
    """Interface for CRM & Loyalty connectors."""
    
    @abstractmethod
    async def get_customer_profile(self, customer_id: str) -> CustomerProfile:
        pass
    
    @abstractmethod
    async def update_loyalty_points(self, customer_id: str, delta: int) -> LoyaltyStatus:
        pass

class PIMConnector(ABC):
    """Interface for PIM connectors."""
    
    @abstractmethod
    async def get_product(self, sku: str) -> ProductData:
        pass
    
    @abstractmethod
    async def update_product(self, sku: str, data: ProductData) -> WritebackResult:
        pass
```

### Feature Flags for Gradual Rollout

New connectors can be rolled out gradually:

```python
from holiday_peak_lib.connectors import ConnectorRegistry

# In configuration
CONNECTOR_INVENTORY_PROVIDER=oracle-fusion
CONNECTOR_INVENTORY_EXPERIMENTAL_SAP=true  # Enable SAP for canary
CONNECTOR_INVENTORY_SAP_ROLLOUT_PERCENT=10  # 10% traffic to SAP

# Registry handles routing
class InventorySCMFactory:
    @classmethod
    def create_with_rollout(cls, config: ConnectorConfig) -> BaseConnector:
        if config.experimental_enabled and random.random() < config.rollout_percent:
            return cls.create(config.experimental_provider, config)
        return cls.create(config.primary_provider, config)
```

## Consequences

### Positive
- **Loose coupling**: Services don't know concrete connector implementations
- **Easy swapping**: Change `CONNECTOR_*_PROVIDER` to switch systems
- **Secure credentials**: Key Vault integration with fallback chain
- **Testability**: Mock connectors for unit/integration tests
- **Extensibility**: Register custom connectors without framework changes

### Negative
- **Indirection**: Factory adds a layer of abstraction
- **Configuration complexity**: Many environment variables to manage
- **Runtime errors**: Unknown connector names fail at runtime, not compile time

### Risks Mitigated
- **Vendor lock-in**: Swappable connectors prevent tight coupling
- **Credential exposure**: Key Vault references in config, not secrets
- **Test pollution**: Mock connectors isolate tests from external systems

## Alternatives Considered

### 1. Direct Connector Instantiation
**Rejected**: Creates tight coupling; changing a connector requires code changes.

### 2. Dependency Injection Framework (e.g., FastAPI Depends)
**Considered**: Works for FastAPI but not for CLI tools, background workers. Registry is framework-agnostic.

### 3. Plugin Architecture with Dynamic Loading
**Deferred**: Over-engineering for v1.x; registry provides sufficient flexibility.

## Implementation Notes

- See `lib/src/holiday_peak_lib/connectors/` for implementation
- Each domain has its own factory under the `connectors/` directory
- Mock connectors live alongside real connectors with `Mock` prefix
- Use `ConnectorRegistry.available()` for admin UIs listing options

## References

- [Factory Pattern](https://refactoring.guru/design-patterns/factory-method)
- [Azure Key Vault References](https://docs.microsoft.com/en-us/azure/app-service/app-service-key-vault-references)
- ADR-003: Adapter Pattern (adapters consume connectors)
- ADR-023: Enterprise Resilience (connectors include resilience patterns)
