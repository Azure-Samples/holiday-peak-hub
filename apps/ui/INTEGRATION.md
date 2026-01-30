# Holiday Peak Hub - Frontend Integration Setup

## Prerequisites

Install required dependencies:

```bash
cd apps/ui
yarn add @azure/msal-browser @azure/msal-react @tanstack/react-query
```

## Environment Configuration

1. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

2. Update `.env.local` with your values:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_ENTRA_CLIENT_ID=your-client-id
   NEXT_PUBLIC_ENTRA_TENANT_ID=your-tenant-id
   ```

## Architecture

### API Layer (`lib/api/`)
- **`client.ts`** - Axios client with request/response interceptors
- **`endpoints.ts`** - Centralized API endpoint definitions

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

## Next Steps

### 1. Install Dependencies
```bash
cd apps/ui
yarn add @azure/msal-browser @azure/msal-react @tanstack/react-query
```

### 2. Add React Query Provider

Create `lib/providers/QueryProvider.tsx`:
```typescript
'use client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, useState } from 'react';

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        retry: 1,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

Update `app/layout.tsx` to include QueryProvider.

### 3. Create React Query Hooks

Example `lib/hooks/useProducts.ts`:
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productService } from '../services/productService';

export function useProducts(filters?: { search?: string; category?: string }) {
  return useQuery({
    queryKey: ['products', filters],
    queryFn: () => productService.list(filters),
  });
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => productService.get(id),
    enabled: !!id,
  });
}
```

### 4. Update Pages to Use Real Data

Replace mock data in pages with service calls. Example:

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
