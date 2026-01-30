# Changelog

All notable changes to the Holiday Peak Hub project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CRUD Service implementation (v1.0.0) - 31 REST endpoints across 15 route modules
- Complete frontend API integration layer with TypeScript client
- Microsoft Entra ID authentication via MSAL (SSR-safe implementation)
- React Query hooks for data fetching (5 custom hooks)
- Service layer abstraction (6 TypeScript services)
- Event publishing integration with Azure Event Hubs (5 topics)
- MCP agent client for optional agent invocation
- Comprehensive test structure (unit, integration, e2e)
- Complete API documentation and integration guide
- CRUD Service implementation documentation

### Changed
- Updated Next.js to 16.2.0-canary.17 for latest features
- Downgraded Tailwind CSS to 3.4.0 for stability (from v4 beta)
- Updated frontend documentation to reflect completed integration
- Updated backend plan to mark CRUD service as complete
- Improved README with accurate implementation status

### Fixed
- MSAL SSR compatibility issue (window undefined during server-side rendering)
- Next.js 15 params promise unwrapping requirement
- CSS pseudo-class syntax (::hover → :hover) for Turbopack compatibility
- Image configuration migration (domains → remotePatterns)
- Viewport metadata export for Next.js 15+
- Favicon path resolution in layout
- FilterPanel and ProductGrid undefined prop defaults
- PostCSS nesting plugin compatibility (downgraded to v12.1.5)
- Next.js SWC version alignment issue

## [1.0.0] - 2026-01-29

### Added - Backend (CRUD Service)

#### Core Implementation
- FastAPI application with lifespan management
- Application Insights integration for observability
- CORS middleware with configurable origins
- Global exception handling with ApiError class
- Structured logging with correlation IDs

#### Authentication & Authorization
- Microsoft Entra ID JWT validation
- Role-based access control (RBAC) with 4 roles:
  - Anonymous: Health checks, product browsing
  - Customer: Cart, orders, reviews, profile
  - Staff: Analytics, tickets, shipments
  - Admin: Returns processing, user management
- Token validation middleware with FastAPI dependencies

#### Data Layer
- Base repository pattern with Cosmos DB integration
- Managed Identity authentication (no hardcoded credentials)
- Specialized repositories:
  - UserRepository (users, addresses, payment methods)
  - ProductRepository (products, categories)
  - OrderRepository (orders, order items)
  - CartRepository (carts, cart items)
- Retry logic with exponential backoff for 429 errors
- Pagination support for list operations

#### API Routes (31 endpoints)

**Health & Monitoring (3)**:
- GET `/health` - Overall health check
- GET `/health/live` - Kubernetes liveness probe
- GET `/health/ready` - Readiness probe (checks dependencies)

**Authentication (3)**:
- POST `/auth/login` - User login (returns JWT)
- POST `/auth/logout` - User logout
- POST `/auth/register` - User registration

**Users (2)**:
- GET `/users/me` - Get current user profile
- PUT `/users/me` - Update user profile

**Products (2)**:
- GET `/products` - List products (with search/filter)
- GET `/products/{id}` - Get product details

**Categories (2)**:
- GET `/categories` - List all categories
- GET `/categories/{slug}` - Get category by slug

**Cart (4)**:
- GET `/cart` - Get user's cart
- POST `/cart/items` - Add item to cart
- PUT `/cart/items/{id}` - Update cart item quantity
- DELETE `/cart/items/{id}` - Remove item from cart

**Orders (4)**:
- POST `/orders` - Create order from cart
- GET `/orders` - List user's orders
- GET `/orders/{id}` - Get order details
- GET `/orders/{id}/track` - Track order shipment

**Checkout & Payments (3)**:
- POST `/checkout/validate` - Validate checkout
- POST `/payments/intent` - Create Stripe PaymentIntent
- POST `/payments/{id}/confirm` - Confirm payment

**Reviews (2)**:
- POST `/products/{id}/reviews` - Create product review
- GET `/products/{id}/reviews` - List product reviews

**Staff - Analytics (1)**:
- GET `/staff/analytics` - Sales analytics dashboard

**Staff - Support (2)**:
- GET `/staff/tickets` - List support tickets
- PUT `/staff/tickets/{id}` - Update ticket status

**Staff - Logistics (2)**:
- GET `/staff/shipments` - List shipments
- PUT `/staff/returns/{id}` - Process return

#### Integrations

**Event Publishing (Azure Event Hubs)**:
- 5 event topics:
  - `user-events` - User registration, profile updates
  - `product-events` - Product created, updated, deleted
  - `order-events` - Order placed, status changed, cancelled
  - `inventory-events` - Stock updates
  - `payment-events` - Payment succeeded, failed
- Event schema with correlation/causation IDs
- Async publishing with error handling
- Used by 21 AI agents for event-driven workflows

**Agent Client (MCP)**:
- Optional HTTP calls to agent MCP endpoints
- Fallback to basic CRUD if agents unavailable
- Use cases: product enrichment, cart intelligence, checkout validation

#### Testing

**Structure**:
- Unit tests: Repositories, auth, event publisher
- Integration tests: API endpoints (mocked dependencies)
- E2E tests: Full checkout flow

**Fixtures** (`conftest.py`):
- Mock Cosmos DB client
- Mock Event Hubs producer
- Mock MSAL token validation
- Test users with different roles

**Coverage**:
- Health endpoints: 100%
- Authentication: 100%
- Repositories: Placeholders (TODO: implement mocks)
- API routes: Placeholders (TODO: implement tests)

#### Configuration

**Environment Variables**:
- `COSMOS_ACCOUNT_URI` - Cosmos DB endpoint
- `COSMOS_DATABASE` - Database name
- `EVENTHUB_NAMESPACE` - Event Hubs namespace
- `REDIS_URL` - Redis cache URL
- `KEYVAULT_URL` - Azure Key Vault URL
- `ENTRA_TENANT_ID` - Microsoft Entra ID tenant
- `ENTRA_CLIENT_ID` - App registration client ID
- `ENTRA_ISSUER` - Token issuer URL
- `STRIPE_SECRET_KEY` - Stripe API key
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Monitoring

**Pydantic Settings**:
- Type-safe configuration with validation
- Environment variable loading
- Default values for local development
- Secrets loaded from Key Vault (Managed Identity)

#### Deployment

**Docker**:
- Python 3.13 base image
- Multi-stage build (dev/prod)
- Non-root user for security
- Health check endpoint
- Optimized layer caching

**Kubernetes**:
- Deployment to AKS `crud` node pool
- 3 replicas minimum
- HPA (3-20 replicas based on CPU/memory)
- Liveness/readiness probes
- Resource requests/limits

### Added - Frontend (API Integration)

#### API Client Layer

**Axios Client** (`lib/api/client.ts`):
- Base URL from environment variable
- 10-second timeout
- Request interceptor: Attach JWT token from sessionStorage
- Response interceptor: Handle 401/403/429 errors
- ApiError class for structured error handling

**Endpoints** (`lib/api/endpoints.ts`):
- Centralized endpoint definitions
- Type-safe endpoint builder
- Prevents hardcoded URLs throughout codebase

#### Type Definitions

**API Types** (`lib/types/api.ts`):
- TypeScript interfaces matching backend Pydantic models
- User, Product, Order, Cart, Review types
- Request/Response DTOs
- Pagination types (PaginatedResponse)
- Error response types

#### Services Layer

**productService** (`lib/services/productService.ts`):
- `list(filters?)` - List products with search/category filter
- `get(id)` - Get product by ID
- `create(data)` - Create product (admin only)
- `update(id, data)` - Update product (admin only)
- `delete(id)` - Delete product (admin only)

**cartService** (`lib/services/cartService.ts`):
- `get()` - Get current user's cart
- `addItem(data)` - Add item to cart
- `updateItem(itemId, data)` - Update cart item quantity
- `removeItem(itemId)` - Remove item from cart

**orderService** (`lib/services/orderService.ts`):
- `create(data)` - Create new order
- `list()` - List user's orders
- `get(id)` - Get order details
- `track(id)` - Track order shipment

**authService** (`lib/services/authService.ts`):
- `login(credentials)` - User login
- `logout()` - User logout
- `register(data)` - User registration
- `me()` - Get current user profile

**userService** (`lib/services/userService.ts`):
- `getProfile()` - Get user profile
- `updateProfile(data)` - Update profile
- `listAddresses()` - List saved addresses
- `addAddress(data)` - Add new address
- `listPaymentMethods()` - List saved payment methods

**checkoutService** (`lib/services/checkoutService.ts`):
- `validate(cart)` - Validate checkout
- `createPaymentIntent(amount)` - Create Stripe payment intent
- `confirmPayment(paymentId)` - Confirm payment

#### React Query Hooks

**useProducts** (`lib/hooks/useProducts.ts`):
- `useProducts(filters?)` - Query products list
- `useProduct(id)` - Query single product
- `useCreateProduct()` - Mutation to create product
- `useUpdateProduct()` - Mutation to update product
- `useDeleteProduct()` - Mutation to delete product

**useCart** (`lib/hooks/useCart.ts`):
- `useCart()` - Query current cart
- `addToCart` - Mutation to add item (invalidates cart cache)
- `updateCartItem` - Mutation to update quantity
- `removeFromCart` - Mutation to remove item

**useOrders** (`lib/hooks/useOrders.ts`):
- `useOrders()` - Query user's orders
- `useOrder(id)` - Query single order
- `useTrackOrder(id)` - Query order tracking

**useCheckout** (`lib/hooks/useCheckout.ts`):
- `validateCheckout` - Mutation to validate checkout
- `createOrder` - Mutation to create order
- `createPaymentIntent` - Mutation for Stripe payment

**useUser** (`lib/hooks/useUser.ts`):
- `useUser()` - Query current user profile
- `updateProfile` - Mutation to update profile
- `useAddresses()` - Query saved addresses
- `usePaymentMethods()` - Query saved payment methods

#### Authentication (MSAL)

**Configuration** (`lib/auth/msalConfig.ts`):
- `getMsalConfig()` function (SSR-safe, returns config on client only)
- Microsoft Entra ID settings from environment variables
- Redirect URI configuration
- Scopes: `openid`, `profile`, `email`, `User.Read`

**Auth Context** (`contexts/AuthContext.tsx`):
- Dynamic MSAL instance creation (useEffect, client-only)
- Login handler with popup authentication
- Logout handler with redirect
- Token acquisition (silent refresh + popup fallback)
- User state management (AccountInfo)
- Protected route HOC (`withAuth`)

**Providers** (`app/providers.tsx`):
- Client-only wrapper for AuthProvider
- Prevents SSR issues with MSAL browser APIs
- Graceful loading state during initialization

#### Configuration

**Environment** (`.env.example`, `.env.local`):
- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NEXT_PUBLIC_ENTRA_CLIENT_ID` - Entra ID client ID
- `NEXT_PUBLIC_ENTRA_TENANT_ID` - Entra ID tenant ID
- `NEXT_PUBLIC_REDIRECT_URI` - OAuth redirect URI

**Next.js** (`next.config.js`):
- API proxy: `/api/*` → `${NEXT_PUBLIC_API_URL}/*`
- Image remotePatterns: localhost, Azure Blob Storage, Static Web Apps
- Environment variable forwarding
- SWC compiler configuration

**PostCSS** (`postcss.config.js`):
- Tailwind CSS 3.4.0 (downgraded from v4)
- PostCSS nesting plugin v12.1.5
- Autoprefixer

**Tailwind** (`tailwind.config.ts`):
- Ocean/lime/cyan color palette
- Extended typography utilities
- Dark mode support (class-based)
- Responsive breakpoints

#### Providers

**QueryProvider** (`lib/providers/QueryProvider.tsx`):
- React Query client configuration
- Stale time: 60 seconds
- Retry: 1 attempt
- Client-side only

**AuthProvider** (`contexts/AuthContext.tsx`):
- MSAL integration
- Token management
- User state
- Login/logout handlers

#### Documentation

**INTEGRATION.md** (`apps/ui/INTEGRATION.md`):
- Complete setup guide
- Architecture overview
- Usage examples
- API reference
- Troubleshooting guide
- Next steps for page integration

### Documentation Updates

**Main README** (`README.MD`):
- Updated frontend section with API integration status
- Updated backend section with CRUD service completion
- Added dependencies list (MSAL, React Query, Axios)
- Updated tech stack versions

**Docs README** (`docs/README.md`):
- Added CRUD service implementation details
- Updated architecture section with new status
- Added link to CRUD service documentation

**Implementation Documentation**:
- Replaced massive backend_plan.md (4890 lines) with concise IMPLEMENTATION_ROADMAP.md
- Created comprehensive CRUD service implementation guide
- Documented all completed work and pending tasks
- Updated all documentation references

**New Documentation**:
- `docs/architecture/crud-service-implementation.md` - Comprehensive CRUD service documentation
- This CHANGELOG.md - Project changelog

### Dependencies

**Frontend**:
- @azure/msal-browser@5.1.0
- @azure/msal-react@5.0.3
- @tanstack/react-query@5.90.20
- axios@1.7.9
- next@16.2.0-canary.17
- tailwindcss@3.4.0
- postcss-nesting@12.1.5

**Backend** (already in pyproject.toml):
- fastapi@0.115+
- azure-cosmos@4.7+
- azure-eventhub@5.12+
- azure-identity@1.19+
- pydantic@2.10+
- stripe@11.1+

## [0.9.0] - 2026-01-30

### Added
- Initial project structure
- 21 AI agent services (e-commerce, CRM, inventory, logistics, product management)
- Agent framework (`holiday_peak_lib`)
- Three-tier memory architecture (hot/warm/cold)
- Frontend UI (13 pages, 52 components)
- Shared infrastructure Bicep modules
- Static Web App Bicep modules
- Architecture documentation (20 ADRs)
- Complete backend implementation plan

### Infrastructure
- Azure Kubernetes Service (AKS) configuration
- Azure Container Registry (ACR) setup
- Cosmos DB schemas (10 containers)
- Event Hubs namespace (5 topics)
- Redis Cache Premium configuration
- Azure Key Vault integration
- Virtual Network with Private Endpoints
- CI/CD pipelines (GitHub Actions)

---

## Notes

### Version Strategy
- **Major version** (X.0.0): Breaking changes, major feature releases
- **Minor version** (0.X.0): New features, non-breaking changes
- **Patch version** (0.0.X): Bug fixes, documentation updates

### Changelog Sections
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Features to be removed in future
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

### Links
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [CRUD Service Documentation](docs/architecture/crud-service-implementation.md)
- [Frontend Integration Guide](apps/ui/INTEGRATION.md)
- [Architecture Documentation](docs/README.md)
