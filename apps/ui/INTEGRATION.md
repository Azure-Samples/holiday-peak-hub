# Holiday Peak Hub - Frontend Integration Guide

**Status**: ✅ Complete  
**Last Updated**: January 29, 2026  
**Version**: 1.0.0

## Overview

Complete frontend-backend integration for the Holiday Peak Hub Next.js application. This guide covers the API client layer, authentication, React Query hooks, and usage patterns.

## What's Included

✅ **API Layer**: Axios client with JWT interceptors, centralized endpoints  
✅ **Services Layer**: 6 TypeScript services (product, cart, order, auth, user, checkout)  
✅ **React Query Hooks**: 5 custom hooks for data fetching and mutations  
✅ **Authentication**: Microsoft Entra ID via MSAL (SSR-safe)  
✅ **Type Safety**: Complete TypeScript interfaces matching backend Pydantic models  
✅ **Configuration**: Environment variables, Next.js config, PostCSS, Tailwind  

## Prerequisites

**Dependencies** (already installed):
```bash
@azure/msal-browser@5.1.0
@azure/msal-react@5.0.3
@tanstack/react-query@5.90.20
axios@1.7.9
```

**Backend Requirements**:
- Azure infrastructure must be provisioned (`azd provision`) and services deployed (`azd deploy`) for the target environment.
- CRUD/Agent APIs must be reachable through cloud APIM endpoint(s) configured in UI env vars.
- Microsoft Entra ID app registration (client ID, tenant ID)

## Environment Configuration

1. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

2. Update `.env.local` with your values:
   ```bash
  NEXT_PUBLIC_CRUD_API_URL=https://<apimName>.azure-api.net
  NEXT_PUBLIC_API_URL=https://<apimName>.azure-api.net
  NEXT_PUBLIC_AGENT_API_URL=https://<apimName>.azure-api.net/agents
   NEXT_PUBLIC_ENTRA_CLIENT_ID=your-client-id
   NEXT_PUBLIC_ENTRA_TENANT_ID=your-tenant-id
   ```

### Unified API Base URL Contract

Shared resolver module: `app/api/_shared/base-url-resolver.ts`

- CRUD env precedence: `NEXT_PUBLIC_CRUD_API_URL` → `NEXT_PUBLIC_API_URL` → `NEXT_PUBLIC_API_BASE_URL` → `CRUD_API_URL`
- Agent env precedence: `NEXT_PUBLIC_AGENT_API_URL` → `AGENT_API_URL` → CRUD aliases above with `/agents` suffix
- CRUD/API base values may be configured either as the APIM gateway root or with a trailing `/api`; the shared resolver normalizes both to the gateway root before proxying.
- Browser runtime:
  - CRUD client (`lib/api/client.ts`) always uses `/api/*` proxy route
  - Agent client (`lib/api/agentClient.ts`) uses `/agent-api/*`
- Server runtime:
  - CRUD and Agent API routes/clients resolve from env precedence above
- Test runtime:
  - CRUD client defaults to `http://localhost:8000`
  - Agent client derives from resolved CRUD base + `/agents` (fallback `/agents`)

This contract is validated by unit tests in `tests/unit/baseUrlResolverContract.test.ts`.

## Runtime Hosting Mode (Azure Static Web Apps + Next.js)

This UI is deployed on **Azure Static Web Apps with Next.js server runtime enabled** (hybrid mode), not as static-only export.

- Production evidence includes `X-Powered-By: Next.js`.
- `/api/*` requests are handled by Next Route Handlers and proxied upstream with `x-holiday-peak-proxy: next-app-api`.
- `next.config.js` uses `output: 'standalone'`, which is compatible with server-side runtime deployment.

### Avoid confusion: Static-only vs Hybrid Next.js on SWA

- **Static-only SWA (no Node runtime)**
  Uses Next static export (`output: 'export'`), serves prebuilt assets only, and does not execute Next Route Handlers/SSR at request time.

- **SWA + Next server runtime (current model)**
  Supports SSR/Server Components/Route Handlers and returns runtime signals such as `X-Powered-By: Next.js` and proxy headers from server handlers.

## Architecture

### API Layer (`lib/api/`)
- **`client.ts`** - Axios client with request/response interceptors
- **`endpoints.ts`** - Centralized API endpoint definitions

### Route Compatibility (Azure Static Web Apps)
- Category and product navigation uses query routes for cloud compatibility:
  - `/category?slug=<categoryId>`
  - `/product?id=<productId>`
- Dynamic routes still exist for local/dev compatibility (`/category/[slug]`, `/product/[id]`).

### Services Layer (`lib/services/`)
- **`productService.ts`** - Product CRUD operations
- **`cartService.ts`** - Cart management
- **`orderService.ts`** - Order operations
- **`authService.ts`** - Authentication
- **`userService.ts`** - User profile management
- **`checkoutService.ts`** - Checkout validation

### Authentication (`lib/auth/` + `contexts/`)
- **`msalConfig.ts`** - Microsoft Entra ID (MSAL) configuration
- **`AuthContext.tsx`** - React context with MSAL integration
  - Login/logout handlers
  - Token management
  - User state
  - Protected route HOC

### Type Definitions (`lib/types/`)
- **`api.ts`** - TypeScript interfaces matching backend Pydantic models

### React Query Hooks (`lib/hooks/`) ✅ Implemented
- **`useProducts.ts`** - Product queries and mutations
- **`useCart.ts`** - Cart queries and mutations with cache invalidation
- **`useOrders.ts`** - Order queries
- **`useCheckout.ts`** - Checkout flow validation
- **`useUser.ts`** - User profile management

### Providers (`lib/providers/`)
- **`QueryProvider.tsx`** ✅ Implemented - React Query configuration with defaults

## Implementation Status

### ✅ Completed Components

1. **API Client Layer** (`lib/api/`):
   - Axios client with request/response interceptors
   - Automatic JWT token attachment from sessionStorage
   - Error handling (401/403/429) with ApiError class
   - Centralized endpoint definitions

2. **Services Layer** (`lib/services/`):
   - `productService.ts` - List, get, create, update, delete products
   - `cartService.ts` - Get cart, add/update/remove items
   - `orderService.ts` - Create order, list orders, get order, track shipment
   - `authService.ts` - Login, logout, register, current user
   - `userService.ts` - Get/update profile, manage addresses/payment methods
   - `checkoutService.ts` - Validate checkout, create payment intent

3. **Authentication** (`lib/auth/` + `contexts/`):
   - MSAL configuration (SSR-safe with dynamic import)
   - AuthContext with login/logout handlers
   - Token management (silent refresh + popup fallback)
   - Protected route HOC (`withAuth`)
   - Client-only provider wrapper

4. **React Query Hooks** (`lib/hooks/`):
   - All hooks implemented with proper cache keys
   - Mutations with automatic cache invalidation
   - Error handling and loading states
   - Stale-time configuration (60s default)

5. **Configuration**:
   - `.env.example` and `.env.local` templates
   - `next.config.js` - API proxy, image remotePatterns
   - `postcss.config.js` - Tailwind CSS 3.4.0
   - `tailwind.config.ts` - Ocean/lime/cyan color palette
   - `app/providers.tsx` - Client-only auth provider
   - `app/layout.tsx` - Root layout with providers

### ⏸️ Pending Work

- Update individual pages to use real API data instead of mocks
- Implement error boundaries for API failures
- Add loading skeletons for better UX
- E2E testing with Cypress/Playwright

## Usage Examples

### Using Services Directly

```typescript
import { productService } from '@/lib/services/productService';

// List products
const products = await productService.list({ search: 'laptop' });

// Get single product
const product = await productService.get('product-id');
```

### Using Authentication

```typescript
import { useAuth } from '@/contexts/AuthContext';

function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuth();

  if (!isAuthenticated) {
    return <button onClick={login}>Login</button>;
  }

  return (
    <div>
      Welcome {user?.name}
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

### Protected Routes

```typescript
import { withAuth } from '@/contexts/AuthContext';

function ProfilePage() {
  return <div>Protected Content</div>;
}

export default withAuth(ProfilePage);
```

### Using React Query Hooks

```typescript
'use client';
import { useProducts } from '@/lib/hooks/useProducts';

function ProductList() {
  const { data: products, isLoading, error } = useProducts({ 
    search: 'laptop',
    category: 'electronics' 
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {products?.map(product => (
        <div key={product.id}>{product.name}</div>
      ))}
    </div>
  );
}
```

### Cart Operations with Mutations

```typescript
'use client';
import { useCart } from '@/lib/hooks/useCart';

function CartButton({ productId }: { productId: string }) {
  const { addToCart } = useCart();

  const handleAddToCart = () => {
    addToCart.mutate({
      productId,
      quantity: 1,
      variantId: 'default',
    });
  };

  return (
    <button onClick={handleAddToCart} disabled={addToCart.isPending}>
      {addToCart.isPending ? 'Adding...' : 'Add to Cart'}
    </button>
  );
}
```

## Configuration Details

### Environment Variables

**Required** (`.env.local`):
```bash
# Cloud Backend API URLs
NEXT_PUBLIC_CRUD_API_URL=https://<apimName>.azure-api.net
NEXT_PUBLIC_API_URL=https://<apimName>.azure-api.net
NEXT_PUBLIC_AGENT_API_URL=https://<apimName>.azure-api.net/agents

# Microsoft Entra ID (Azure AD)
NEXT_PUBLIC_ENTRA_CLIENT_ID=your-client-id
NEXT_PUBLIC_ENTRA_TENANT_ID=your-tenant-id

# Optional: Custom redirect URI
NEXT_PUBLIC_REDIRECT_URI=http://localhost:3000
```

### Next.js Configuration

**API Proxy** (`next.config.js`):
```javascript
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: `${process.env.NEXT_PUBLIC_CRUD_API_URL}/api/:path*`,
    },
  ];
}
```

**Image Domains**:
```javascript
images: {
  remotePatterns: [
    {
      protocol: 'http',
      hostname: 'localhost',
      port: '8000',
    },
    {
      protocol: 'https',
      hostname: '*.blob.core.windows.net',
    },
    {
      protocol: 'https',
      hostname: '*.azurestaticapps.net',
    },
  ],
}
```

### Tailwind CSS Configuration

**Version**: 3.4.0 (downgraded from v4 for stability)

**Custom Colors** (`tailwind.config.ts`):
```typescript
colors: {
  ocean: {
    50: '#e6f2ff',
    // ... full palette
    950: '#001a33',
  },
  lime: { /* ... */ },
  cyan: { /* ... */ },
}
```

### PostCSS Configuration

**Plugins** (`postcss.config.js`):
```javascript
plugins: {
  'tailwindcss/nesting': 'postcss-nesting',  // v12.1.5
  tailwindcss: {},
  autoprefixer: {},
}
```

## Troubleshooting

### Common Issues

#### 1. MSAL "window is not defined" Error
**Fixed**: AuthContext now uses dynamic MSAL initialization in `useEffect`

```typescript
// ✅ Correct (SSR-safe)
useEffect(() => {
  const config = getMsalConfig();
  const instance = new PublicClientApplication(config);
  setMsalInstance(instance);
}, []);
```

#### 2. Next.js 15 Params as Promise
**Fixed**: Unwrap params with `React.use()`

```typescript
// ✅ Correct
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // ...
}
```

#### 3. CSS Pseudo-element Error
**Fixed**: Use `:hover` not `::hover`

```css
/* ✅ Correct */
.highlight-border:hover {
  @apply border-lime-400;
}
```

#### 4. FilterPanel/ProductGrid Undefined Props
**Fixed**: Provide default values

```typescript
// ✅ Correct
function FilterPanel({ filterGroups = [] }) {
  return filterGroups.map(/* ... */);
}
```

### Next.js Version Compatibility

**Current**: Next.js 16.2.0-canary.17

**Notes**:
- Stricter CSS validation (use `:hover` not `::hover`)
- Params are promises in async components
- `viewport` export required (not in metadata)
- Image `domains` deprecated (use `remotePatterns`)

## Next Steps

### 1. ✅ Dependencies Installed
All required packages are already installed:
- @azure/msal-browser@5.1.0
- @azure/msal-react@5.0.3
- @tanstack/react-query@5.90.20
- axios@1.7.9

### 2. ✅ React Query Provider Added
`lib/providers/QueryProvider.tsx` is implemented and included in `app/providers.tsx`.

### 3. ✅ React Query Hooks Created
All hooks are implemented in `lib/hooks/`:
- useProducts.ts
- useCart.ts
- useOrders.ts
- useCheckout.ts
- useUser.ts

### 4. ⏸️ Update Pages to Use Real Data

Replace mock data in pages with API services:

**Before** (`app/product/[id]/page.tsx`):
```typescript
const product = { /* mock data */ };
```

**After**:
```typescript
'use client';
import { useProduct } from '@/lib/hooks/useProducts';

export default function ProductPage({ params }: { params: { id: string } }) {
  const { data: product, isLoading, error } = useProduct(params.id);

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <ErrorState error={error} />;
  if (!product) return <NotFound />;

  return <ProductDetails product={product} />;
}
```

## Development

Start both backend and frontend:

**Terminal 1 - Backend (CRUD Service)**:
```bash
cd apps/crud-service/src
uvicorn crud_service.main:app --reload
```

**Terminal 2 - Frontend**:
```bash
cd apps/ui
yarn dev
```

Access: http://localhost:3000

## Testing

```bash
cd apps/ui
yarn test
```

## Build for Production

```bash
cd apps/ui
yarn build
```

## Deployment

See `.infra/modules/static-web-app/README.md` for Azure Static Web Apps deployment instructions.
