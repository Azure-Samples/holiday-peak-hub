# Enterprise Connectors

This folder contains adapters for integrating Holiday Peak Hub with enterprise retail systems. Each connector implements the interfaces defined in `lib/src/holiday_peak_lib/adapters/` and provides connectivity to specific vendor platforms.

## Architecture

```
connectors/
├── README.md                    # This file
├── common/                      # Shared utilities
│   ├── auth/                    # OAuth, API key, SAML helpers
│   ├── transformers/            # Data mapping utilities
│   ├── testing/                 # Mock server factories
│   └── protocols.py             # Compatibility re-export (canonical: lib)
│
├── inventory_scm/               # Inventory & Supply Chain
│   ├── sap_s4hana/
│   ├── oracle_scm/
│   ├── manhattan_omni/
│   ├── blue_yonder/
│   ├── dynamics365_scm/
│   └── infor_wms/
│
├── crm_loyalty/                 # CRM, Loyalty, CDP
│   ├── salesforce/
│   ├── dynamics365_ce/
│   ├── adobe_aep/
│   ├── braze/
│   └── twilio_segment/
│
├── pim_dam/                     # Product Information & Digital Assets
│   ├── salsify/
│   ├── inriver/
│   ├── akeneo/
│   ├── pimcore/
│   ├── sap_hybris_pim/
│   ├── informatica_p360/
│   ├── adobe_aem/
│   ├── bynder/
│   ├── cloudinary/
│   └── sitecore_hub/
│
├── commerce_order/              # Commerce & Order Management
│   ├── salesforce_commerce/
│   ├── adobe_commerce/
│   ├── sap_commerce/
│   ├── shopify/
│   ├── commercetools/
│   ├── vtex/
│   └── manhattan_oms/
│
├── data_analytics/              # Data & Analytics
│   ├── azure_synapse/
│   ├── snowflake/
│   ├── databricks/
│   ├── google_analytics/
│   └── adobe_analytics/
│
├── integration_messaging/       # iPaaS & Messaging
│   ├── mulesoft/
│   ├── kafka_confluent/
│   ├── boomi/
│   └── ibm_sterling/
│
├── identity_security/           # Identity & Consent
│   ├── okta_auth0/
│   └── onetrust/
│
└── workforce_ops/               # Store Ops & Workforce
    ├── ukg_kronos/
    ├── zebra_reflexis/
    └── workjam/
```

## Design Principles

### 1. Product Enrichment: Internal Data Only

AI agents enrich product data **exclusively from company-owned systems**:
- PIM systems hold master product attributes
- DAM systems provide approved imagery
- CRM systems contribute customer segments
- Analytics platforms deliver behavioral insights

Agents DO NOT generate content without explicit source data.

### 2. Connector Contract

Every connector MUST:

```python
from holiday_peak_lib.adapters.base import BaseAdapter
from holiday_peak_lib.connectors import PIMConnectorProtocol

class VendorConnector(BaseAdapter, PIMConnectorProtocol):
    """
    Connector for Vendor System.
    
    Environment Variables:
        VENDOR_BASE_URL: API base URL
        VENDOR_API_KEY: API key or OAuth client ID
        VENDOR_API_SECRET: Secret (if OAuth)
        
    REST API Reference:
        https://vendor.com/api-docs
    """
    
    async def _fetch_impl(self, query: dict) -> list[dict]:
        """Implement fetch with vendor-specific API calls."""
        ...
```

### 3. Domain Interfaces

Connectors implement typed protocols from `holiday_peak_lib.connectors.protocols`:

```python
from typing import Protocol
from pydantic import BaseModel

class ProductData(BaseModel):
    sku: str
    title: str
    description: str
    attributes: dict
    images: list[str]
    category_path: list[str]

class PIMConnectorProtocol(Protocol):
    """Interface for PIM system connectors."""
    
    async def get_product(self, sku: str) -> ProductData: ...
    async def list_products(self, category: str | None = None) -> list[ProductData]: ...
    async def search_products(self, query: str) -> list[ProductData]: ...
    async def get_product_assets(self, sku: str) -> list[AssetData]: ...
```

### 4. Testing

Each connector includes:
- Unit tests with mocked HTTP responses
- Integration tests (skipped in CI, run against sandbox)
- Mock server for local development

```python
# tests/test_salsify.py
import pytest
from connectors.pim_dam.salsify import SalsifyConnector

@pytest.fixture
def mock_salsify(httpx_mock):
    httpx_mock.add_response(
        url="https://app.salsify.com/api/v1/products/SKU123",
        json={"id": "SKU123", "name": "Test Product", ...}
    )
    return httpx_mock

async def test_get_product(mock_salsify):
    connector = SalsifyConnector(api_key="test-key")
    product = await connector.get_product("SKU123")
    assert product.sku == "SKU123"
```

## Configuration

Connectors read configuration from environment variables. Example `.env`:

```bash
# Salsify PIM
SALSIFY_API_KEY=your-api-key
SALSIFY_ORG_ID=your-org-id

# Cloudinary DAM
CLOUDINARY_CLOUD_NAME=your-cloud
CLOUDINARY_API_KEY=your-key
CLOUDINARY_API_SECRET=your-secret

# Shopify Commerce
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your-token
SHOPIFY_API_VERSION=2024-01

# Salesforce CRM
SALESFORCE_INSTANCE_URL=https://yourorg.salesforce.com
SALESFORCE_CLIENT_ID=your-client-id
SALESFORCE_CLIENT_SECRET=your-secret
SALESFORCE_USERNAME=your-username
SALESFORCE_PASSWORD=your-password
```

## Usage with CRUD Service

Register connectors in services via `ConnectorRegistry`:

```python
# apps/<service>/src/main.py
from holiday_peak_lib.connectors import ConnectorRegistry
from connectors.pim_dam.salsify import SalsifyConnector
from connectors.pim_dam.cloudinary import CloudinaryConnector
from connectors.commerce_order.shopify import ShopifyConnector

# Initialize connectors
pim = SalsifyConnector.from_env()
dam = CloudinaryConnector.from_env()
commerce = ShopifyConnector.from_env()

# Register with connector registry
registry = ConnectorRegistry()
await registry.register("pim", pim, domain="pim")
await registry.register("dam", dam, domain="dam")
await registry.register("commerce", commerce, domain="commerce")

# Now CRUD endpoints and agents use these connectors
```

## Adding a New Connector

1. Create folder: `connectors/<domain>/<vendor>/`
2. Implement adapter extending `BaseAdapter`
3. Implement domain protocol(s)
4. Add tests with mocked responses
5. Document REST API endpoints used
6. Create GitHub issue tracking the connector
7. Update this README

## REST API Documentation References

Each connector documents the vendor REST APIs it uses:

| Vendor | API Docs |
|--------|----------|
| Salsify | https://developers.salsify.com/reference |
| inRiver | https://apidoc.inriver.com/ |
| Akeneo | https://api.akeneo.com/ |
| Cloudinary | https://cloudinary.com/documentation/admin_api |
| Shopify | https://shopify.dev/api/admin-rest |
| commercetools | https://docs.commercetools.com/api |
| Salesforce | https://developer.salesforce.com/docs/apis |
| SAP S/4HANA | https://api.sap.com/package/SAPS4HANACloud |
| Oracle SCM | https://docs.oracle.com/en/cloud/saas/supply-chain-management/ |

## Related Documentation

- [Integration Strategy](../docs/roadmap/011-retail-system-integration-strategy.md)
- [ADR-003: Adapter Pattern](../docs/architecture/adrs/adr-003-adapter-pattern.md)
- [ADR-012: Adapter Boundaries](../docs/architecture/adrs/adr-012-adapter-boundaries.md)
- [BaseAdapter Implementation](../lib/src/holiday_peak_lib/adapters/base.py)
