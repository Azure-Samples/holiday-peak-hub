# Frontend Implementation Plan

**Version**: 2.0  
**Date**: 2026-01-30  
**Status**: Ready for Implementation

## Overview

This document defines the complete frontend implementation with updated page structure, color system, responsive design, and backend service mappings.

## Table of Contents

1. [Page Structure](#page-structure)
2. [Color System](#color-system)
3. [Page-to-Service Mapping](#page-to-service-mapping)
4. [Component Usage](#component-usage)
5. [Authentication & Roles](#authentication--roles)
6. [Implementation Phases](#implementation-phases)

---

## Page Structure

### Anonymous Users (5 Pages)

**No authentication required** - Public access

| # | Page | Route | Purpose |
|---|------|-------|---------|
| 1 | **Homepage** | `/` | Landing page with featured products and categories |
| 2 | **Category Page** | `/category/[slug]` | Product listing by category with filters |
| 3 | **Product Page** | `/product/[id]` | Detailed product information and specifications |
| 4 | **Reviews** | `/product/[id]/reviews` | Product reviews and ratings |
| 5 | **Order** | `/order/[id]` | Order status lookup (with order ID) |

---

### Logged In Users - Customers (4 Pages)

**Role**: `customer`

| # | Page | Route | Purpose |
|---|------|-------|---------|
| 6 | **Checkout** | `/checkout` | Complete purchase with payment |
| 7 | **Order Tracking** | `/my-orders` | View all customer orders |
| 8 | **Dashboard** | `/dashboard` | Customer overview with recommendations |
| 9 | **Profile** | `/profile` | User profile and preferences |

---

### Logged In Workers - Staff (5 Pages)

**Role**: `staff`

| # | Page | Route | Purpose |
|---|------|-------|---------|
| 10 | **Sales Analytics** | `/staff/sales` | Sales metrics (page views, per product, per category) |
| 11 | **Requests** | `/staff/requests` | Customer support requests and inquiries |
| 12 | **Shippings** | `/staff/shippings` | Shipping management and updates |
| 13 | **Logistic Tracking** | `/staff/logistics` | Real-time logistics and delivery tracking |
| 14 | **Customer Profiles** | `/staff/customers` | Customer information and history |

---

### Logged In Admins (1 Page)

**Role**: `admin`

| # | Page | Route | Purpose |
|---|------|-------|---------|
| 15 | **Admin Portal** | `/admin` | Gateway to all backend service capabilities |

**Admin capabilities** are exposed via backend services:
- Product management
- Inventory management
- Pricing configuration
- Campaign management
- System configuration
- User management
- Analytics and reporting

---

## Color System

### Design System Palette

**Primary Colors**:
```css
Ocean Blue: #0077BE (Primary actions, headers)
Lime Green: #32CD32 (Success states, CTAs)
Cyan: #00CED1 (Accents, highlights)
White: #FFFFFF (Backgrounds, text on dark)
Dark Grey: #2D3748 (Text, dark backgrounds)
```

**Extended Palette**:
```css
/* Ocean Blue Variants */
--ocean-blue-50: #E6F4FB
--ocean-blue-100: #CCE9F7
--ocean-blue-200: #99D3EF
--ocean-blue-300: #66BDE7
--ocean-blue-400: #33A7DF
--ocean-blue-500: #0077BE (Primary)
--ocean-blue-600: #005F98
--ocean-blue-700: #004772
--ocean-blue-800: #00304C
--ocean-blue-900: #001826

/* Lime Green Variants */
--lime-green-50: #F0FBF0
--lime-green-100: #E1F8E1
--lime-green-200: #C3F1C3
--lime-green-300: #A5EAA5
--lime-green-400: #87E387
--lime-green-500: #32CD32 (Primary)
--lime-green-600: #28A428
--lime-green-700: #1E7B1E
--lime-green-800: #145214
--lime-green-900: #0A290A

/* Cyan Variants */
--cyan-50: #E6FAFA
--cyan-100: #CCF5F5
--cyan-200: #99EBEB
--cyan-300: #66E1E1
--cyan-400: #33D7D7
--cyan-500: #00CED1 (Primary)
--cyan-600: #00A5A7
--cyan-700: #007C7D
--cyan-800: #005254
--cyan-900: #00292A

/* Neutrals */
--white: #FFFFFF
--grey-50: #F7FAFC
--grey-100: #EDF2F7
--grey-200: #E2E8F0
--grey-300: #CBD5E0
--grey-400: #A0AEC0
--grey-500: #718096
--grey-600: #4A5568
--grey-700: #2D3748 (Primary)
--grey-800: #1A202C
--grey-900: #171923
```

### Dark Mode Palette

```css
/* Dark Mode Colors */
--dark-bg-primary: #171923
--dark-bg-secondary: #1A202C
--dark-bg-tertiary: #2D3748
--dark-text-primary: #F7FAFC
--dark-text-secondary: #E2E8F0
--dark-ocean-blue: #66BDE7
--dark-lime-green: #87E387
--dark-cyan: #66E1E1
```

### Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        ocean: {
          50: '#E6F4FB',
          100: '#CCE9F7',
          200: '#99D3EF',
          300: '#66BDE7',
          400: '#33A7DF',
          500: '#0077BE',
          600: '#005F98',
          700: '#004772',
          800: '#00304C',
          900: '#001826',
        },
        lime: {
          50: '#F0FBF0',
          100: '#E1F8E1',
          200: '#C3F1C3',
          300: '#A5EAA5',
          400: '#87E387',
          500: '#32CD32',
          600: '#28A428',
          700: '#1E7B1E',
          800: '#145214',
          900: '#0A290A',
        },
        cyan: {
          50: '#E6FAFA',
          100: '#CCF5F5',
          200: '#99EBEB',
          300: '#66E1E1',
          400: '#33D7D7',
          500: '#00CED1',
          600: '#00A5A7',
          700: '#007C7D',
          800: '#005254',
          900: '#00292A',
        },
      },
    },
  },
  darkMode: 'class',
};
```

### Color Usage Guidelines

**Light Mode**:
- Primary actions: `ocean-500`
- Success states: `lime-500`
- Accents: `cyan-500`
- Backgrounds: `white`, `grey-50`
- Text: `grey-900`, `grey-700`
- Borders: `grey-200`, `grey-300`

**Dark Mode**:
- Primary actions: `ocean-300`
- Success states: `lime-400`
- Accents: `cyan-300`
- Backgrounds: `grey-900`, `grey-800`
- Text: `grey-50`, `grey-200`
- Borders: `grey-700`, `grey-600`

---

## Page-to-Service Mapping

### Anonymous Pages

#### 1. Homepage (`/`)

**Services**:
- `ecommerce-catalog-search` - Featured products
- `crm-segmentation-personalization` - Personalized recommendations (if has session)
- `product-management-assortment-optimization` - Featured categories

**Components**:
- `MainLayout`
- `Navigation`
- `ProductGrid` (featured products)
- `Card` (category cards)
- `Button`

**Features**:
- Hero section with seasonal promotions
- Featured product grid (8-12 products)
- Category showcase (6-8 categories)
- Search bar integration
- Dark mode toggle

---

#### 2. Category Page (`/category/[slug]`)

**Services**:
- `ecommerce-catalog-search` - Product search and filtering
- `inventory-health-check` - Real-time stock status
- `product-management-assortment-optimization` - Sort by popularity

**Components**:
- `ShopLayout`
- `FilterPanel` (price, brand, attributes)
- `ProductGrid`
- `ProductCard`
- `Breadcrumb`
- `Pagination`

**Features**:
- Advanced filters (price range, brand, color, size)
- Sort options (relevance, price, popularity)
- Grid/list view toggle
- Infinite scroll or pagination
- Stock availability indicators

---

#### 3. Product Page (`/product/[id]`)

**Services**:
- `ecommerce-product-detail-enrichment` - Full product details (ACP compliant)
- `inventory-health-check` - Real-time inventory
- `logistics-eta-computation` - Delivery estimates
- `ecommerce-cart-intelligence` - Related products

**Components**:
- `MainLayout`
- `ProductCard` (hero)
- `Tabs` (description, specs, shipping)
- `Button` (add to cart)
- `Badge` (stock status, discount)
- `Rating` (average rating)
- `Carousel` (image gallery)

**Features**:
- Image gallery with zoom
- Variant selection (size, color)
- Add to cart / Add to wishlist
- Stock status and quantity selector
- Estimated delivery date
- Related products
- Breadcrumb navigation

---

#### 4. Reviews (`/product/[id]/reviews`)

**Services**:
- `ecommerce-product-detail-enrichment` - Review data
- `crm-profile-aggregation` - Verified purchase badges

**Components**:
- `MainLayout`
- `Rating` (overall rating)
- `Card` (review cards)
- `Avatar` (reviewer avatars)
- `Pagination`

**Features**:
- Overall rating breakdown (5-star distribution)
- Individual review cards
- Sort by (most recent, highest rating, verified purchases)
- Filter by rating
- Helpful votes

---

#### 5. Order (`/order/[id]`)

**Services**:
- `ecommerce-order-status` - Order details
- `logistics-eta-computation` - Delivery updates
- `logistics-route-issue-detection` - Delay alerts

**Components**:
- `OrderTrackingLayout`
- `Timeline` (order status)
- `Card` (order summary)
- `Badge` (status badges)
- `Alert` (delay notifications)

**Features**:
- Order status timeline
- Tracking number
- Estimated delivery date
- Order items list
- Shipping address
- Contact support button

---

### Customer Pages

#### 6. Checkout (`/checkout`)

**Role**: `customer`

**Services**:
- `ecommerce-cart-intelligence` - Cart validation
- `ecommerce-checkout-support` - Checkout validation
- `inventory-reservation-validation` - Stock reservation
- `logistics-carrier-selection` - Shipping options

**Components**:
- `CheckoutLayout`
- `CheckoutForm`
- `Steps` (progress indicator)
- `FormField` (address, payment)
- `PriceDisplay` (order summary)
- `Alert` (validation errors)

**Features**:
- Multi-step checkout (shipping, payment, review)
- Address validation
- Payment method selection
- Order summary with pricing breakdown
- Promo code application
- Terms and conditions checkbox

---

#### 7. Order Tracking (`/my-orders`)

**Role**: `customer`

**Services**:
- `ecommerce-order-status` - All customer orders
- `logistics-eta-computation` - Delivery updates
- `logistics-returns-support` - Return requests

**Components**:
- `MainLayout`
- `DataTable` (orders list)
- `Badge` (status)
- `Button` (view details, track, return)
- `Tabs` (active, completed, cancelled)

**Features**:
- Order history table
- Filter by status
- Search by order ID
- Quick actions (track, return, reorder)
- Download invoices

---

#### 8. Dashboard (`/dashboard`)

**Role**: `customer`

**Services**:
- `crm-profile-aggregation` - User profile summary
- `crm-segmentation-personalization` - Personalized recommendations
- `ecommerce-order-status` - Recent orders
- `inventory-health-check` - Wishlist stock updates

**Components**:
- `MainLayout`
- `StatCard` (order stats)
- `ProductGrid` (recommendations)
- `ListItem` (recent activity)
- `Card` (wishlist items)

**Features**:
- Welcome message
- Order statistics (total orders, pending, completed)
- Recent orders
- Personalized product recommendations
- Wishlist with stock alerts
- Quick actions (reorder, track)

---

#### 9. Profile (`/profile`)

**Role**: `customer`

**Services**:
- `crm-profile-aggregation` - User profile data
- `crm-segmentation-personalization` - Preference management

**Components**:
- `MainLayout`
- `Tabs` (profile, preferences, addresses, payment)
- `FormField` (editable fields)
- `Button` (save, cancel)
- `Card` (address cards, payment cards)

**Features**:
- Personal information editing
- Email preferences (marketing, notifications)
- Saved addresses (add, edit, delete, set default)
- Saved payment methods
- Password change
- Account deletion

---

### Staff Pages

#### 10. Sales Analytics (`/staff/sales`)

**Role**: `staff`

**Services**:
- `crm-campaign-intelligence` - Sales metrics
- `ecommerce-catalog-search` - Product performance
- `inventory-health-check` - Stock turnover

**Components**:
- `MainLayout`
- `Tabs` (overview, products, categories)
- `Chart` (line, bar, pie charts)
- `StatCard` (KPIs)
- `DataTable` (top products)

**Features**:
- **Overview Tab**:
  - Total sales, revenue, orders
  - Sales trends (daily, weekly, monthly)
  - Conversion rate
- **Products Tab**:
  - Top selling products
  - Page views per product
  - Add-to-cart rate
- **Categories Tab**:
  - Sales by category
  - Category trends
  - Stock levels by category

---

#### 11. Requests (`/staff/requests`)

**Role**: `staff`

**Services**:
- `crm-support-assistance` - Support tickets
- `crm-profile-aggregation` - Customer context
- `logistics-returns-support` - Return requests

**Components**:
- `MainLayout`
- `DataTable` (requests list)
- `Badge` (priority, status)
- `Modal` (request details)
- `FormField` (response form)

**Features**:
- Support ticket list
- Filter by status (open, in-progress, closed)
- Filter by type (inquiry, complaint, return)
- Priority indicators
- Customer context panel
- Quick response templates
- Assign to agent

---

#### 12. Shippings (`/staff/shippings`)

**Role**: `staff`

**Services**:
- `logistics-eta-computation` - Shipping management
- `logistics-carrier-selection` - Carrier performance
- `logistics-route-issue-detection` - Delay alerts

**Components**:
- `MainLayout`
- `DataTable` (shipments list)
- `Badge` (status)
- `Alert` (delays)
- `Modal` (shipment details)
- `Timeline` (tracking events)

**Features**:
- Shipment list with tracking numbers
- Filter by status (pending, in-transit, delivered)
- Search by order ID or tracking number
- Delay alerts and notifications
- Carrier performance metrics
- Bulk actions (print labels, update status)

---

#### 13. Logistic Tracking (`/staff/logistics`)

**Role**: `staff`

**Services**:
- `logistics-eta-computation` - Real-time tracking
- `logistics-route-issue-detection` - Issue detection
- `logistics-carrier-selection` - Carrier monitoring

**Components**:
- `MainLayout`
- `Timeline` (delivery timeline)
- `Chart` (delivery performance)
- `DataTable` (active shipments)
- `Alert` (route issues)
- `Badge` (status)

**Features**:
- Real-time shipment map (if available)
- Active shipments dashboard
- Delivery performance metrics (on-time %, delays)
- Route issue alerts
- ETA updates
- Carrier comparison

---

#### 14. Customer Profiles (`/staff/customers`)

**Role**: `staff`

**Services**:
- `crm-profile-aggregation` - Customer data
- `crm-segmentation-personalization` - Segment information
- `ecommerce-order-status` - Order history

**Components**:
- `MainLayout`
- `DataTable` (customer list)
- `ProfileCard` (customer details)
- `ListItem` (order history)
- `Badge` (segments, loyalty tier)
- `Tabs` (profile, orders, interactions)

**Features**:
- Customer list with search
- Customer profile view
- Order history
- Segment and cohort information
- Lifetime value
- Support interaction history
- Notes and tags

---

### Admin Pages

#### 15. Admin Portal (`/admin`)

**Role**: `admin`

**Services**: Access to all backend service capabilities

**Components**:
- `MainLayout`
- `Card` (service cards)
- `Icon` (service icons)
- `Button` (navigate to service)

**Features**:
- **Service Dashboard**:
  - Quick links to all backend services
  - Service health indicators
  - Recent activity feed

**Backend Service Capabilities** (accessed via API):
- **Product Management**:
  - `product-management-normalization-classification`
  - `product-management-acp-transformation`
  - `product-management-consistency-validation`
  - `product-management-assortment-optimization`
- **Inventory Management**:
  - `inventory-health-check`
  - `inventory-jit-replenishment`
  - `inventory-reservation-validation`
  - `inventory-alerts-triggers`
- **Pricing & Campaigns**:
  - `ecommerce-checkout-support` (pricing rules)
  - `crm-campaign-intelligence`
- **System Configuration**:
  - User management
  - Role assignment
  - System settings
- **Analytics**:
  - Advanced reporting
  - Data export
  - Performance monitoring

---

## Component Usage

### Atoms (19 components)

Used across all pages:
- `Button` - Primary actions, CTAs
- `Input` - Form fields, search
- `Icon` - Visual indicators
- `Badge` - Status indicators, tags
- `Avatar` - User avatars, reviews
- `Spinner` - Loading states
- `Rating` - Product ratings
- `Switch` - Toggle preferences
- `Skeleton` - Loading placeholders
- `Divider` - Visual separation
- `Text` - Typography
- `Label` - Form labels
- `Checkbox` - Multi-select
- `Radio` - Single select
- `Select` - Dropdowns
- `Textarea` - Comments, notes
- `Tooltip` - Help text
- `ProgressBar` - Upload, loading
- `Chart` - Data visualization (atomic wrapper)

### Molecules (20 components)

- `Card` - Content containers (products, orders, stats)
- `FormField` - Form input groups
- `ProductCard` - Product displays
- `CartItem` - Cart line items
- `SearchInput` - Search with icon
- `Breadcrumb` - Navigation path
- `Tabs` - Content organization
- `Popover` - Context menus
- `Steps` - Checkout progress
- `SectionTitle` - Page sections
- `StatCard` - KPI cards
- `AvatarGroup` - Multiple users
- `MenuList` - Navigation menus
- `ListItem` - List entries
- `Timeline` - Event timelines
- `ProfileCard` - User profiles
- `PriceDisplay` - Price formatting
- `Dropdown` - Action menus
- `Alert` - Notifications
- `Modal` - Dialogs

### Organisms (9 components)

- `Navigation` - Site header (all pages)
- `ProductGrid` - Product listings
- `FilterPanel` - Search filters
- `ShoppingCart` - Cart sidebar
- `CheckoutForm` - Checkout flow
- `OrderTracker` - Order status
- `DataTable` - Data lists (staff/admin)
- `TaskList` - Request lists
- `NotificationCenter` - Alerts

### Templates (4 layouts)

- `MainLayout` - Standard pages (homepage, product, profile)
- `ShopLayout` - Category/search pages
- `CheckoutLayout` - Checkout flow
- `OrderTrackingLayout` - Order tracking

---

## Authentication & Roles

### Role Definitions

```typescript
export enum Role {
  ANONYMOUS = 'anonymous',
  CUSTOMER = 'customer',
  STAFF = 'staff',
  ADMIN = 'admin',
}
```

### Permission Matrix

| Page Category | Anonymous | Customer | Staff | Admin |
|---------------|-----------|----------|-------|-------|
| Homepage | ✅ | ✅ | ✅ | ✅ |
| Category | ✅ | ✅ | ✅ | ✅ |
| Product | ✅ | ✅ | ✅ | ✅ |
| Reviews | ✅ | ✅ | ✅ | ✅ |
| Order (lookup) | ✅ | ✅ | ✅ | ✅ |
| Checkout | ❌ | ✅ | ✅ | ✅ |
| My Orders | ❌ | ✅ | ✅ | ✅ |
| Dashboard | ❌ | ✅ | ✅ | ✅ |
| Profile | ❌ | ✅ | ✅ | ✅ |
| Sales | ❌ | ❌ | ✅ | ✅ |
| Requests | ❌ | ❌ | ✅ | ✅ |
| Shippings | ❌ | ❌ | ✅ | ✅ |
| Logistics | ❌ | ❌ | ✅ | ✅ |
| Customers | ❌ | ❌ | ✅ | ✅ |
| Admin | ❌ | ❌ | ❌ | ✅ |

### Route Protection

```typescript
// middleware.ts
const ROUTE_ACCESS: Record<string, Role[]> = {
  '/': [Role.ANONYMOUS, Role.CUSTOMER, Role.STAFF, Role.ADMIN],
  '/category/*': [Role.ANONYMOUS, Role.CUSTOMER, Role.STAFF, Role.ADMIN],
  '/product/*': [Role.ANONYMOUS, Role.CUSTOMER, Role.STAFF, Role.ADMIN],
  '/order/*': [Role.ANONYMOUS, Role.CUSTOMER, Role.STAFF, Role.ADMIN],
  '/checkout': [Role.CUSTOMER, Role.STAFF, Role.ADMIN],
  '/my-orders': [Role.CUSTOMER, Role.STAFF, Role.ADMIN],
  '/dashboard': [Role.CUSTOMER, Role.STAFF, Role.ADMIN],
  '/profile': [Role.CUSTOMER, Role.STAFF, Role.ADMIN],
  '/staff/*': [Role.STAFF, Role.ADMIN],
  '/admin': [Role.ADMIN],
};
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

**Goal**: Set up color system and core layouts

**Tasks**:
1. ✅ Update Tailwind config with new color palette
2. ✅ Create dark mode provider
3. ✅ Update `MainLayout` with new colors
4. ✅ Update `ShopLayout` with new colors
5. ✅ Update `CheckoutLayout` with new colors
6. ✅ Update `OrderTrackingLayout` with new colors
7. ✅ Update `Navigation` component with new colors
8. ✅ Test dark mode toggle across all layouts

**Deliverables**:
- Color system implemented
- All layouts updated
- Dark mode functional

---

### Phase 2: Anonymous Pages (Week 2)

**Goal**: Implement public-facing pages

**Tasks**:
1. ✅ Homepage (`/`)
   - Hero section
   - Featured products
   - Category cards
2. ✅ Category page (`/category/[slug]`)
   - Product grid
   - Filter panel
   - Sorting
3. ✅ Product page (`/product/[id]`)
   - Product details
   - Image gallery
   - Add to cart
4. ✅ Reviews (`/product/[id]/reviews`)
   - Review list
   - Rating breakdown
5. ✅ Order lookup (`/order/[id]`)
   - Order status
   - Tracking timeline

**Deliverables**:
- 5 anonymous pages functional
- Service integrations complete
- Responsive design verified

---

### Phase 3: Customer Pages (Week 3)

**Goal**: Implement authenticated customer pages

**Tasks**:
1. ✅ Checkout (`/checkout`)
   - Multi-step form
   - Payment integration
2. ✅ Order tracking (`/my-orders`)
   - Order history
   - Filter and search
3. ✅ Dashboard (`/dashboard`)
   - User stats
   - Recommendations
4. ✅ Profile (`/profile`)
   - Profile editing
   - Preferences
   - Saved addresses

**Deliverables**:
- 4 customer pages functional
- Authentication working
- Profile management complete

---

### Phase 4: Staff Pages (Week 4)

**Goal**: Implement staff management pages

**Tasks**:
1. ✅ Sales analytics (`/staff/sales`)
   - Sales charts
   - Product metrics
   - Category performance
2. ✅ Requests (`/staff/requests`)
   - Support tickets
   - Customer context
3. ✅ Shippings (`/staff/shippings`)
   - Shipment list
   - Tracking updates
4. ✅ Logistics (`/staff/logistics`)
   - Real-time tracking
   - Route issues
5. ✅ Customer profiles (`/staff/customers`)
   - Customer list
   - Order history

**Deliverables**:
- 5 staff pages functional
- RBAC enforced
- Service integrations complete

---

### Phase 5: Admin & Polish (Week 5)

**Goal**: Complete admin portal and polish

**Tasks**:
1. ✅ Admin portal (`/admin`)
   - Service dashboard
   - Quick links
2. ✅ Performance optimization
   - Image optimization
   - Code splitting
   - Caching
3. ✅ Accessibility audit
   - WCAG 2.1 AA compliance
   - Keyboard navigation
   - Screen reader testing
4. ✅ E2E testing
   - Critical user flows
   - Cross-browser testing
5. ✅ Documentation
   - Component usage
   - Page documentation

**Deliverables**:
- All 15 pages complete
- Performance optimized (Lighthouse >90)
- Accessibility compliant
- Documentation complete

---

## Success Criteria

### Functional Requirements
- ✅ All 15 pages implemented
- ✅ Authentication and RBAC working
- ✅ All backend services integrated
- ✅ Color system consistent
- ✅ Dark mode functional

### Performance Requirements
- ✅ Lighthouse score > 90
- ✅ First Contentful Paint < 1.5s
- ✅ Time to Interactive < 3s
- ✅ Cumulative Layout Shift < 0.1

### Quality Requirements
- ✅ Test coverage > 80%
- ✅ WCAG 2.1 AA compliance
- ✅ Zero TypeScript errors
- ✅ Zero ESLint errors

### Design Requirements
- ✅ Responsive (mobile, tablet, desktop)
- ✅ Color palette applied consistently
- ✅ Dark mode on all pages
- ✅ AG-UI Protocol compliant
- ✅ ACP compliant (product pages)

---

## References

- [Architecture Decision Records](ADRs.md)
- [Component Documentation](../../ui/components/COMPONENT_README.md)
- [Frontend Governance](../governance/frontend-governance.md)
- [Backend Services](components.md#apps-domain-services)

---

**Next Steps**: Begin Phase 1 - Update color system and layouts
