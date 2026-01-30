# Atomic Design Component Library

This directory contains a complete atomic design system for the e-commerce platform.

## Structure

```
atomic/
├── types/          # Shared TypeScript types
├── utils.ts        # Utility functions (cn, formatCurrency, etc.)
├── atoms/          # Basic building blocks (14 components)
├── molecules/      # Composed components (10 components)
├── organisms/      # Complex features (6 components)
└── templates/      # Page layouts (4 templates)
```

## Usage

### Import Everything

```tsx
import { Button, Input, Card, ProductCard, Navigation, ShopLayout } from '@/components/atomic';
```

### Import Specific Categories

```tsx
// Atoms only
import { Button, Input, Badge } from '@/components/atomic/atoms';

// Molecules only
import { Card, FormField, Alert } from '@/components/atomic/molecules';

// Organisms only
import { Navigation, ShoppingCart, CheckoutForm } from '@/components/atomic/organisms';

// Templates only
import { MainLayout, ShopLayout } from '@/components/atomic/templates';
```

## Component Inventory

### Atoms (14)
Basic UI building blocks:
- **Button** - 7 variants, 5 sizes, loading/disabled states
- **Icon** - react-icons wrapper
- **Input** - Text input with validation
- **Label** - Form label with required indicator
- **Checkbox** - Checkbox with indeterminate state
- **Radio** - Radio button with group support
- **Select** - Dropdown select (single/multi)
- **Textarea** - Multi-line text input
- **Badge** - Status badge with variants
- **Text** - Typography system (h1-h6, p, span)
- **Divider** - Horizontal/vertical separator
- **Avatar** - User avatar with fallback
- **Skeleton** - Loading placeholder
- **Spinner** - Loading indicator

### Molecules (10)
Composed components:
- **Card** - Content container with header/footer
- **FormField** - Form input wrapper with label/error
- **Alert** - Notification message (7 variants)
- **Dropdown** - Menu dropdown (consolidated from 9 implementations)
- **Modal** - Dialog/modal (consolidated from 3 implementations)
- **SearchInput** - Search with debounce and keyboard nav
- **Breadcrumb** - Navigation breadcrumb
- **PriceDisplay** - Product price with MSRP/sale
- **ProductCard** - Product listing card
- **CartItem** - Shopping cart item

### Organisms (6)
Complex features:
- **FilterPanel** - Faceted search filters (checkbox, radio, color, range)
- **ProductGrid** - Product listing with grid/list toggle
- **Navigation** - Main app navigation bar
- **ShoppingCart** - Full cart with items and summary
- **CheckoutForm** - Multi-step checkout process
- **OrderTracker** - Order status and tracking

### Templates (4)
Page layouts:
- **MainLayout** - Base layout with nav and footer
- **ShopLayout** - Shop page with filters and products
- **CheckoutLayout** - Checkout process layout
- **OrderTrackingLayout** - Order tracking page layout

## Features

### TypeScript Support
All components are fully typed with TypeScript:
```tsx
import type { ButtonProps, ProductCardProps } from '@/components/atomic';
```

### Dark Mode
All components support dark mode via Tailwind's `dark:` classes.

### React Hook Form Integration
Form components support both controlled and RHF patterns:
```tsx
// Controlled
<Input value={value} onChange={onChange} />

// React Hook Form
<Input useRHF {...register('field')} />
```

### Consistent Props
All components support:
- `className` - Custom styling
- `testId` - Testing identifiers
- `ariaLabel` - Accessibility

### Utilities
Shared utilities in `utils.ts`:
- `cn()` - Class name merger (clsx + tailwind-merge)
- `formatCurrency()` - Currency formatting
- `sizeClasses` - Size class mappings
- `variantClasses` - Variant class mappings
- Validation helpers

## Examples

### Building a Shop Page

```tsx
import { ShopLayout } from '@/components/atomic/templates';
import { MainLayout } from '@/components/atomic/templates';

export default function ShopPage() {
  return (
    <MainLayout>
      <ShopLayout
        filterGroups={filters}
        products={products}
        onFilterChange={handleFilterChange}
        onAddToCart={handleAddToCart}
      />
    </MainLayout>
  );
}
```

### Building a Checkout Flow

```tsx
import { CheckoutLayout } from '@/components/atomic/templates';

export default function CheckoutPage() {
  return (
    <CheckoutLayout
      currentStep={step}
      orderSummary={summary}
      onPlaceOrder={handlePlaceOrder}
    />
  );
}
```

### Building a Custom Form

```tsx
import { FormField, Input, Button, Card } from '@/components/atomic';

export function ContactForm() {
  return (
    <Card>
      <FormField label="Email" required>
        <Input type="email" useRHF {...register('email')} />
      </FormField>
      <Button variant="primary" type="submit">
        Send
      </Button>
    </Card>
  );
}
```

## Migration from Old Components

Old components are still present in the codebase. To migrate:

1. Update imports:
```tsx
// Before
import Button from '@/components/Button';

// After
import { Button } from '@/components/atomic/atoms';
```

2. Update props (most are compatible):
```tsx
// Button props are mostly the same
<Button variant="primary" size="lg" onClick={handleClick}>
  Click Me
</Button>
```

3. Form components now have `useRHF` prop:
```tsx
// Before
<Input {...register('field')} />

// After
<Input useRHF {...register('field')} />
```

## Documentation

See `/docs/ECOMMERCE_UI_PLAN.md` for the complete implementation plan.
See `/ui/COMPONENT_ANALYSIS.md` for component analysis.
See `/ui/SHARED_PATTERNS.md` for pattern consolidation details.
