/**
 * Shared Types for Atomic Design Components
 * Defines common types, variants, and interfaces used across all atomic components
 */

// ===== COMMON VARIANTS =====

export type Size = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
export type Variant = 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info' | 'ghost';
export type ColorScheme = 'blue' | 'green' | 'red' | 'yellow' | 'gray' | 'purple' | 'pink' | 'indigo';
export type Rounded = 'none' | 'sm' | 'md' | 'lg' | 'full';
export type Spacing = 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
export type FontWeight = 'light' | 'normal' | 'medium' | 'semibold' | 'bold';
export type TextAlign = 'left' | 'center' | 'right' | 'justify';

// ===== BASE COMPONENT PROPS =====

export interface BaseComponentProps {
  /** Custom CSS class names */
  className?: string;
  /** Custom inline styles */
  style?: React.CSSProperties;
  /** Test ID for testing purposes */
  testId?: string;
  /** Accessibility label */
  ariaLabel?: string;
}

export interface InteractiveProps extends BaseComponentProps {
  /** Whether the component is disabled */
  disabled?: boolean;
  /** Whether the component is in loading state */
  loading?: boolean;
  /** Click handler */
  onClick?: (event: React.MouseEvent) => void;
}

// ===== FORM-RELATED TYPES =====

export interface FormFieldBaseProps extends BaseComponentProps {
  /** Field name (for form submission) */
  name: string;
  /** Field label */
  label?: string;
  /** Field placeholder */
  placeholder?: string;
  /** Error message */
  error?: string;
  /** Helper text */
  hint?: string;
  /** Whether the field is required */
  required?: boolean;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Success message */
  success?: string;
}

export type InputType =
  | 'text'
  | 'email'
  | 'password'
  | 'number'
  | 'tel'
  | 'url'
  | 'search'
  | 'date'
  | 'datetime-local'
  | 'month'
  | 'time'
  | 'week';

// ===== E-COMMERCE TYPES =====

export interface Product {
  sku: string;
  title: string;
  description: string;
  brand: string;
  category: string;
  price: number;
  msrp?: number;
  salePrice?: number;
  currency: string;
  images: string[];
  thumbnail: string;
  rating?: number;
  reviewCount?: number;
  inStock: boolean;
  stockLevel?: number;
  availableSizes?: string[];
  availableColors?: string[];
  tags?: string[];
}

export interface CartItem {
  sku: string;
  title: string;
  thumbnail: string;
  quantity: number;
  price: number;
  size?: string;
  color?: string;
  maxQuantity?: number;
  inStock: boolean;
}

export interface ShippingAddress {
  firstName: string;
  lastName: string;
  addressLine1: string;
  addressLine2?: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
  phone: string;
}

export interface ShippingMethod {
  id: string;
  name: string;
  description: string;
  price: number;
  estimatedDays: number;
  carrier: string;
}

export interface OrderSummary {
  subtotal: number;
  tax: number;
  shipping: number;
  discount: number;
  total: number;
  currency: string;
}

export interface Order {
  orderId: string;
  orderNumber: string;
  date: string;
  status: OrderStatus;
  items: CartItem[];
  summary: OrderSummary;
  shippingAddress: ShippingAddress;
  trackingNumber?: string;
}

export type OrderStatus =
  | 'pending'
  | 'processing'
  | 'shipped'
  | 'in_transit'
  | 'out_for_delivery'
  | 'delivered'
  | 'cancelled'
  | 'refunded';

export interface TrackingEvent {
  timestamp: string;
  event: string;
  location: string;
  description?: string;
}

export interface Shipment {
  trackingId: string;
  carrier: string;
  status: OrderStatus;
  estimatedDelivery: string;
  events: TrackingEvent[];
}

// ===== CART INTELLIGENCE TYPES =====

export interface CartInsights {
  abandonmentRisk: 'low' | 'medium' | 'high';
  insight: string;
  recommendations: Product[];
  priceDropAlerts: PriceAlert[];
  stockWarnings: StockWarning[];
}

export interface PriceAlert {
  sku: string;
  oldPrice: number;
  newPrice: number;
  savingsPercent: number;
}

export interface StockWarning {
  sku: string;
  stockLevel: number;
  message: string;
  severity: 'info' | 'warning' | 'error';
}

// ===== VALIDATION TYPES =====

export interface ValidationResult {
  isValid: boolean;
  blockers: ValidationBlocker[];
  warnings: ValidationWarning[];
}

export interface ValidationBlocker {
  type: 'pricing' | 'inventory' | 'shipping' | 'payment';
  message: string;
  affectedSku?: string;
}

export interface ValidationWarning {
  type: 'pricing' | 'inventory' | 'shipping';
  message: string;
  affectedSku?: string;
}

// ===== FILTER & SORT TYPES =====

export interface FilterOption {
  id: string;
  label: string;
  value: string | number | boolean;
  count?: number;
}

export interface FilterGroup {
  id: string;
  label: string;
  type: 'checkbox' | 'radio' | 'range' | 'color';
  options: FilterOption[];
}

export type SortOption = {
  key: string;
  label: string;
  value: string;
};

// ===== PAGINATION TYPES =====

export interface PaginationProps extends BaseComponentProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
}

// ===== ANALYTICS & METRICS =====

export interface Metric {
  id: string;
  label: string;
  value: number | string;
  unit?: string;
  change?: number;
  changeDirection?: 'up' | 'down' | 'neutral';
  trend?: number[];
}

// ===== NOTIFICATION TYPES =====

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actionLabel?: string;
  actionUrl?: string;
}
