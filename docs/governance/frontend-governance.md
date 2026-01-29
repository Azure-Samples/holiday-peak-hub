# Frontend Development Rules and Policies

**Version**: 1.0  
**Last Updated**: 2026-01-30  
**Owner**: Frontend Team

## Overview

This document defines the coding standards, conventions, and policies for frontend development in the Holiday Peak Hub project. All frontend code must adhere to these rules to ensure consistency, maintainability, and quality.

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Code Style and Linting](#code-style-and-linting)
3. [Component Development](#component-development)
4. [State Management](#state-management)
5. [API Integration](#api-integration)
6. [AG-UI Protocol Compliance](#ag-ui-protocol-compliance)
7. [ACP Frontend Compliance](#acp-frontend-compliance)
8. [Authentication and Security](#authentication-and-security)
9. [Testing Requirements](#testing-requirements)
10. [Performance Guidelines](#performance-guidelines)
11. [Accessibility Standards](#accessibility-standards)
12. [Documentation Requirements](#documentation-requirements)

---

## Tech Stack

### Mandatory Stack

**Framework**:
- Next.js 15.1.6
- React 19.0.0
- TypeScript 5.7.2

**Styling**:
- Tailwind CSS 4.0.0
- CSS Modules (when Tailwind is insufficient)

**State Management**:
- Redux Toolkit 2.5.0 (global state)
- TanStack Query (server state)
- React Context (component-level state)

**Data Fetching**:
- TanStack Query (React Query)
- Axios for HTTP client

**Forms**:
- React Hook Form
- Zod for validation

**Testing**:
- Jest (unit tests)
- React Testing Library (component tests)
- Playwright (E2E tests)

**Utilities**:
- date-fns (date manipulation)
- lodash-es (utility functions, tree-shakeable)
- clsx (conditional classnames)

### Prohibited Libraries

❌ **DO NOT USE**:
- Moment.js (use date-fns instead)
- jQuery (use native DOM APIs or React)
- Class-based CSS frameworks (use Tailwind instead)
- Non-standard state management (Redux Saga, MobX)

---

## Code Style and Linting

### ESLint Configuration

**Mandatory**: Follow ESLint 7 configuration.

```json
{
  "extends": [
    "next/core-web-vitals",
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended"
  ],
  "rules": {
    "no-console": ["warn", { "allow": ["warn", "error"] }],
    "no-debugger": "error",
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "@typescript-eslint/explicit-function-return-type": "off",
    "@typescript-eslint/no-explicit-any": "warn",
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off"
  }
}
```

### TypeScript Rules

✅ **DO**:
- Use TypeScript for all `.tsx` and `.ts` files
- Define explicit types for props and function parameters
- Use `interface` for object types, `type` for unions/intersections
- Enable `strict` mode in `tsconfig.json`
- Avoid `any` type; use `unknown` when type is truly unknown

❌ **DO NOT**:
- Use `@ts-ignore` without explanation comment
- Mix JavaScript and TypeScript files
- Use implicit `any` types
- Define types inline (extract to separate type files)

### Naming Conventions

**Files**:
- Components: `PascalCase.tsx` (e.g., `Button.tsx`)
- Hooks: `camelCase.ts` with `use` prefix (e.g., `useCart.ts`)
- Utilities: `camelCase.ts` (e.g., `formatPrice.ts`)
- Types: `PascalCase.ts` (e.g., `ProductTypes.ts`)
- Constants: `SCREAMING_SNAKE_CASE.ts` (e.g., `API_ENDPOINTS.ts`)

**Variables**:
- Constants: `SCREAMING_SNAKE_CASE`
- Variables/Functions: `camelCase`
- Components: `PascalCase`
- Types/Interfaces: `PascalCase`
- Boolean variables: `is`, `has`, `should` prefix (e.g., `isLoading`, `hasError`)

**React**:
- Component files: `ComponentName.tsx`
- Props interface: `ComponentNameProps`
- State interface: `ComponentNameState`

### Code Formatting

**Prettier Configuration**:
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "always"
}
```

---

## Component Development

### Atomic Design Principles

**Reference**: [ADR-016: Atomic Design System](../architecture/adrs/adr-016-atomic-design-system.md)

**Component Hierarchy**:
1. **Atoms**: Basic building blocks (Button, Input, Icon)
2. **Molecules**: Simple composed components (Card, FormField)
3. **Organisms**: Complex composed components (Navigation, ProductGrid)
4. **Templates**: Page-level layouts (MainLayout, ShopLayout)
5. **Pages**: Complete application screens

### Component Structure

**Standard Component Template**:
```typescript
// components/atoms/Button.tsx
import React from 'react';
import clsx from 'clsx';

export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
  'aria-label'?: string;
  // AG-UI Protocol support
  agAction?: string;
  agTarget?: string;
  agId?: string;
  agContext?: Record<string, any>;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled = false,
      children,
      onClick,
      className,
      type = 'button',
      agAction,
      agTarget,
      agId,
      agContext,
      ...props
    },
    ref
  ) => {
    const baseClasses = 'font-medium rounded-lg transition-colors focus:outline-none focus:ring-2';
    
    const variantClasses = {
      primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
      secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500',
      outline: 'border border-gray-300 bg-transparent hover:bg-gray-50 focus:ring-gray-500',
      ghost: 'bg-transparent hover:bg-gray-100 focus:ring-gray-500',
      danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    };
    
    const sizeClasses = {
      xs: 'px-2 py-1 text-xs',
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-5 py-2.5 text-lg',
      xl: 'px-6 py-3 text-xl',
    };
    
    return (
      <button
        ref={ref}
        type={type}
        className={clsx(
          baseClasses,
          variantClasses[variant],
          sizeClasses[size],
          {
            'opacity-50 cursor-not-allowed': disabled || loading,
          },
          className
        )}
        disabled={disabled || loading}
        onClick={onClick}
        data-ag-component="button"
        data-ag-action={agAction}
        data-ag-target={agTarget}
        data-ag-id={agId}
        data-ag-context={agContext ? JSON.stringify(agContext) : undefined}
        {...props}
      >
        {loading ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Loading...
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
```

### Component Rules

✅ **DO**:
- Use functional components with hooks
- Export component as named export
- Define props interface before component
- Use `React.forwardRef` when component needs ref
- Set `displayName` for debugging
- Include AG-UI attributes for agent interoperability
- Support dark mode via Tailwind classes
- Include ARIA attributes for accessibility
- Use TypeScript for all components

❌ **DO NOT**:
- Use class components (except Error Boundaries)
- Define components inside other components
- Use inline styles (use Tailwind classes)
- Create components without TypeScript types
- Forget to memoize expensive computations
- Mix business logic with UI logic

### Component Organization

**Directory Structure**:
```
components/
├── atoms/
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── index.ts          # Barrel export
│   └── __tests__/
│       └── Button.test.tsx
├── molecules/
│   ├── Card.tsx
│   ├── FormField.tsx
│   ├── index.ts
│   └── __tests__/
│       └── Card.test.tsx
├── organisms/
│   ├── Navigation.tsx
│   ├── ProductGrid.tsx
│   ├── index.ts
│   └── __tests__/
│       └── Navigation.test.tsx
├── templates/
│   ├── MainLayout.tsx
│   ├── ShopLayout.tsx
│   ├── index.ts
│   └── __tests__/
│       └── MainLayout.test.tsx
├── types/
│   └── index.ts
├── utils/
│   └── utils.ts
└── index.ts              # Public API
```

### Import/Export Rules

**Barrel Exports**:
```typescript
// components/atoms/index.ts
export { Button } from './Button';
export { Input } from './Input';
export { Icon } from './Icon';
export type { ButtonProps } from './Button';
export type { InputProps } from './Input';
```

**Import Order**:
1. React and third-party libraries
2. Internal libraries and utilities
3. Components
4. Types
5. Styles

```typescript
// ✅ Correct order
import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';

import { formatPrice } from '@/lib/utils';
import { Button, Card } from '@/components';
import type { Product } from '@/types';

import styles from './ProductCard.module.css';
```

---

## State Management

### State Management Rules

**Redux Toolkit** (global application state):
- User authentication state
- Shopping cart state
- Global UI state (theme, modals)

**TanStack Query** (server state):
- API data fetching
- Caching and synchronization
- Pagination and infinite scroll

**React Context** (component-level state):
- Theme provider
- Locale provider
- Feature flags

**useState/useReducer** (local component state):
- Form state (with React Hook Form)
- UI toggles and temporary state

### Redux Slice Template

```typescript
// store/slices/cartSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { ACPCartItem } from '@/lib/acp/types';

interface CartState {
  items: ACPCartItem[];
  total: number;
  loading: boolean;
  error: string | null;
}

const initialState: CartState = {
  items: [],
  total: 0,
  loading: false,
  error: null,
};

const cartSlice = createSlice({
  name: 'cart',
  initialState,
  reducers: {
    addItem: (state, action: PayloadAction<ACPCartItem>) => {
      const existingItem = state.items.find(item => item.id === action.payload.id);
      if (existingItem) {
        existingItem.quantity += action.payload.quantity;
      } else {
        state.items.push(action.payload);
      }
      state.total = calculateTotal(state.items);
    },
    removeItem: (state, action: PayloadAction<string>) => {
      state.items = state.items.filter(item => item.id !== action.payload);
      state.total = calculateTotal(state.items);
    },
    clearCart: (state) => {
      state.items = [];
      state.total = 0;
    },
  },
});

export const { addItem, removeItem, clearCart } = cartSlice.actions;
export default cartSlice.reducer;

function calculateTotal(items: ACPCartItem[]): number {
  return items.reduce((sum, item) => sum + item.product.price.amount * item.quantity, 0);
}
```

### TanStack Query Usage

```typescript
// hooks/api/useProducts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productClient } from '@/lib/api/clients/product';

export function useProduct(productId: string) {
  return useQuery({
    queryKey: ['product', productId],
    queryFn: () => productClient.getProduct(productId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!productId,
  });
}

export function useUpdateProduct() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      productClient.updateProduct(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['product', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}
```

---

## API Integration

**Reference**: [ADR-020: API Client Architecture](../architecture/adrs/adr-020-api-client-architecture.md)

### Service Client Rules

✅ **DO**:
- Create service client classes extending `ServiceClient`
- Define Zod schemas for all request/response types
- Use TypeScript interfaces for type safety
- Handle errors gracefully with try/catch
- Log all API calls for debugging
- Implement retry logic for transient failures

❌ **DO NOT**:
- Make direct `fetch` calls from components
- Skip response validation
- Ignore error responses
- Store API tokens in component state
- Hardcode API URLs

### Custom Hook Pattern

**Standard Pattern**:
```typescript
// hooks/api/useCart.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { cartClient } from '@/lib/api/clients/cart';

export function useCart(cartId?: string) {
  const queryClient = useQueryClient();
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['cart', cartId],
    queryFn: () => cartClient.getCart(cartId!),
    enabled: !!cartId,
  });
  
  const addToCart = useMutation({
    mutationFn: cartClient.addItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
  
  return {
    cart: data,
    isLoading,
    error,
    addToCart,
  };
}
```

---

## AG-UI Protocol Compliance

**Reference**: [ADR-017: AG-UI Protocol Integration](../architecture/adrs/adr-017-ag-ui-protocol.md)

### Required Annotations

**All Interactive Elements**:
```typescript
<button
  data-ag-component="button"
  data-ag-action="add-to-cart"
  data-ag-target="product"
  data-ag-id={productId}
  data-ag-context={JSON.stringify({ sku, price, quantity })}
>
  Add to Cart
</button>
```

### AG-UI Rules

✅ **DO**:
- Add `data-ag-*` attributes to all interactive elements
- Expose application state to `window.__AG_UI_STATE__`
- Register all agent-callable actions in action registry
- Validate action payloads with Zod schemas
- Log all agent interactions

❌ **DO NOT**:
- Expose sensitive data in AG-UI state
- Allow unauthenticated agent actions
- Skip action validation
- Forget to update state on changes

---

## ACP Frontend Compliance

**Reference**: [ADR-018: ACP Frontend Integration](../architecture/adrs/adr-018-acp-frontend.md)

### Product Data Rules

✅ **DO**:
- Transform all backend product data to ACP format
- Validate products against ACP schema
- Use `ACPProduct` type from `@/lib/acp/types`
- Display ACP-compliant product information
- Include ACP metadata in product cards

❌ **DO NOT**:
- Display raw backend product data
- Skip ACP validation
- Modify ACP schema without versioning
- Lose data during transformation

### ACP Usage Example

```typescript
import { useACPProduct } from '@/hooks/useACPProduct';
import { ACPTransformer } from '@/lib/acp/transformer';
import { ACPValidator } from '@/lib/acp/validator';

function ProductPage({ productId }: { productId: string }) {
  const { data: product, isLoading } = useACPProduct(productId);
  
  if (!product) return null;
  
  return (
    <div>
      <h1>{product.name}</h1>
      <p>{product.category.name}</p>
      <span>${product.price.amount} {product.price.currency}</span>
      <span>{product.inventory.status}</span>
    </div>
  );
}
```

---

## Authentication and Security

**Reference**: [ADR-019: Authentication and RBAC](../architecture/adrs/adr-019-authentication-rbac.md)

### Authentication Rules

✅ **DO**:
- Use JWT tokens stored in httpOnly cookies
- Implement token refresh before expiry
- Protect all sensitive routes with middleware
- Check user roles and permissions
- Log all authentication events

❌ **DO NOT**:
- Store tokens in localStorage or sessionStorage
- Expose sensitive user data in client state
- Skip CSRF protection
- Allow unauthenticated access to admin pages
- Trust client-side role checks alone

### Protected Route Pattern

```typescript
// app/admin/inventory/page.tsx
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Role, Permission } from '@/lib/auth/types';

export default function InventoryPage() {
  return (
    <ProtectedRoute
      requiredRoles={[Role.ADMIN, Role.MANAGER, Role.STAFF]}
      requiredPermissions={[Permission.VIEW_INVENTORY]}
    >
      {/* Page content */}
    </ProtectedRoute>
  );
}
```

---

## Testing Requirements

### Test Coverage Requirements

**Minimum Coverage**:
- Unit tests: 80% coverage
- Component tests: 75% coverage
- Integration tests: 60% coverage

### Unit Testing

**Test Every**:
- Utility functions
- Hooks
- State reducers
- Service clients
- Validators and transformers

**Example**:
```typescript
// __tests__/utils/formatPrice.test.ts
import { formatPrice } from '@/lib/utils/formatPrice';

describe('formatPrice', () => {
  it('formats USD price correctly', () => {
    expect(formatPrice(1299.99, 'USD')).toBe('$1,299.99');
  });
  
  it('handles zero price', () => {
    expect(formatPrice(0, 'USD')).toBe('$0.00');
  });
  
  it('formats EUR price correctly', () => {
    expect(formatPrice(1299.99, 'EUR')).toBe('€1,299.99');
  });
});
```

### Component Testing

**Test Every Component**:
```typescript
// components/atoms/__tests__/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../Button';

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });
  
  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
  
  it('disables button when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByText('Click me')).toBeDisabled();
  });
  
  it('shows loading state', () => {
    render(<Button loading>Click me</Button>);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
```

### E2E Testing

**Critical User Flows**:
- User registration and login
- Product browsing and search
- Add to cart and checkout
- Order tracking
- Admin inventory management

---

## Performance Guidelines

### Performance Budget

**Target Metrics**:
- First Contentful Paint (FCP): < 1.5s
- Largest Contentful Paint (LCP): < 2.5s
- Time to Interactive (TTI): < 3.5s
- Total Blocking Time (TBT): < 300ms
- Cumulative Layout Shift (CLS): < 0.1

### Optimization Techniques

✅ **DO**:
- Use Next.js Image component for images
- Implement lazy loading for below-the-fold content
- Use React.memo for expensive components
- Implement virtual scrolling for large lists
- Use dynamic imports for code splitting
- Optimize bundle size with tree-shaking
- Prefetch critical data
- Use Next.js ISR for static content

❌ **DO NOT**:
- Load unnecessary JavaScript
- Use large unoptimized images
- Skip lazy loading
- Re-render unnecessarily
- Block main thread with heavy computations

---

## Accessibility Standards

### WCAG 2.1 AA Compliance

**Required**:
- Semantic HTML elements
- ARIA attributes where needed
- Keyboard navigation support
- Focus management
- Color contrast ratio ≥ 4.5:1
- Alt text for all images
- Form labels and error messages

### Accessibility Checklist

✅ **DO**:
- Use semantic HTML (`<button>`, `<nav>`, `<main>`, `<article>`)
- Add ARIA labels to icon buttons
- Implement keyboard navigation (Tab, Enter, Escape)
- Provide focus indicators
- Include skip navigation links
- Test with screen readers
- Support dark mode
- Ensure color is not the only indicator

❌ **DO NOT**:
- Use `<div>` for buttons
- Remove focus outlines
- Use color alone for information
- Forget alt text on images
- Create keyboard traps
- Use low contrast colors

---

## Documentation Requirements

### Component Documentation

**Every Component Must Include**:
1. Purpose and use cases
2. Props interface with descriptions
3. Usage examples
4. Accessibility notes
5. AG-UI integration (if applicable)

**Example**:
```typescript
/**
 * Button Component
 * 
 * A flexible button component supporting multiple variants, sizes, and states.
 * Fully accessible with keyboard navigation and screen reader support.
 * 
 * @example
 * ```tsx
 * <Button variant="primary" size="md" onClick={handleClick}>
 *   Click me
 * </Button>
 * ```
 * 
 * @accessibility
 * - Supports keyboard navigation (Enter/Space)
 * - Includes focus indicators
 * - Disabled state properly announced
 * - Loading state announced to screen readers
 * 
 * @ag-ui
 * - Supports data-ag-* attributes for agent interactions
 * - Action context can be passed via agContext prop
 */
export const Button: React.FC<ButtonProps> = ({ ... }) => { ... };
```

### Code Comments

✅ **DO**:
- Document complex logic
- Explain non-obvious decisions
- Add TODOs with ticket references
- Document workarounds and hacks

❌ **DO NOT**:
- State the obvious
- Leave commented-out code
- Write misleading comments
- Skip updating comments when code changes

---

## References

- [ADR-015: Next.js 15 with App Router](../architecture/adrs/adr-015-nextjs-app-router.md)
- [ADR-016: Atomic Design System](../architecture/adrs/adr-016-atomic-design-system.md)
- [ADR-017: AG-UI Protocol](../architecture/adrs/adr-017-ag-ui-protocol.md)
- [ADR-018: ACP Frontend Integration](../architecture/adrs/adr-018-acp-frontend.md)
- [ADR-019: Authentication and RBAC](../architecture/adrs/adr-019-authentication-rbac.md)
- [ADR-020: API Client Architecture](../architecture/adrs/adr-020-api-client-architecture.md)
- [Frontend Architecture Plan](../architecture/FRONTEND_ARCHITECTURE_PLAN.md)
- [Component Documentation](../../ui/components/COMPONENT_README.md)

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-01-30 | Initial documentation | Frontend Team |
