/**
 * TypeScript types matching backend API models
 */

// User types
export interface User {
  user_id: string;
  email: string;
  name: string;
  roles: string[];
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  phone?: string;
  created_at: string;
}

export interface UpdateProfileRequest {
  name?: string;
  phone?: string;
}

// Product types
export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  category_id: string;
  image_url?: string;
  in_stock: boolean;
  rating?: number;
  review_count?: number;
  features?: string[];
  media?: Array<{ url: string; type?: string }>;
  inventory?: Record<string, unknown>;
  related?: Array<Record<string, unknown>>;
}

// Category types
export interface Category {
  id: string;
  name: string;
  description?: string;
  parent_id?: string;
  image_url?: string;
}

// Cart types
export interface CartItem {
  product_id: string;
  quantity: number;
  price: number;
}

export interface Cart {
  user_id: string;
  items: CartItem[];
  total: number;
}

export interface AddToCartRequest {
  product_id: string;
  quantity: number;
}

// Order types
export interface OrderItem {
  product_id: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  user_id: string;
  items: OrderItem[];
  total: number;
  status: string;
  created_at: string;
  tracking?: Record<string, unknown>;
  eta?: Record<string, unknown>;
  carrier?: Record<string, unknown>;
}

export interface CreateOrderRequest {
  shipping_address_id: string;
  payment_method_id: string;
}

// Checkout types
export interface CheckoutValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  estimated_total: number;
  estimated_shipping: number;
  estimated_tax: number;
}

// Payment types
export interface ProcessPaymentRequest {
  order_id: string;
  payment_method_id: string;
  amount: number;
}

export interface Payment {
  id: string;
  order_id: string;
  amount: number;
  status: string;
  transaction_id?: string;
  created_at: string;
}

// Review types
export interface Review {
  id: string;
  product_id: string;
  user_id: string;
  rating: number;
  title: string;
  comment: string;
  created_at: string;
}

export interface CreateReviewRequest {
  product_id: string;
  rating: number;
  title: string;
  comment: string;
}

// Staff types
export interface SalesAnalytics {
  total_revenue: number;
  total_orders: number;
  average_order_value: number;
  top_products: any[];
}

export interface Ticket {
  id: string;
  user_id: string;
  subject: string;
  status: string;
  priority: string;
  created_at: string;
}

export interface Return {
  id: string;
  order_id: string;
  user_id: string;
  status: string;
  reason: string;
  created_at: string;
}

export interface Shipment {
  id: string;
  order_id: string;
  status: string;
  carrier: string;
  tracking_number: string;
  created_at: string;
}

// Truth Layer Admin types

export interface SchemaField {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  required: boolean;
  description?: string;
  enum_values?: string[];
}

export interface CategorySchema {
  id: string;
  category: string;
  version: string;
  fields: SchemaField[];
  created_at: string;
  updated_at: string;
}

export interface TenantConfig {
  tenant_id: string;
  auto_approve_threshold: number;
  enrichment_enabled: boolean;
  hitl_enabled: boolean;
  writeback_enabled: boolean;
  writeback_dry_run: boolean;
  feature_flags: Record<string, boolean>;
  updated_at: string;
}

export interface TruthAnalyticsSummary {
  overall_completeness: number;
  total_products: number;
  enrichment_jobs_processed: number;
  auto_approved: number;
  sent_to_hitl: number;
  queue_pending: number;
  queue_approved: number;
  queue_rejected: number;
  avg_review_time_minutes: number;
  acp_exports: number;
  ucp_exports: number;
}

export interface CompletenessBreakdown {
  category: string;
  completeness: number;
  product_count: number;
}

export interface PipelineThroughput {
  timestamp: string;
  ingested: number;
  enriched: number;
  approved: number;
  rejected: number;
}

// API Response wrappers
export interface ApiResponse<T> {
  data: T;
  status: number;
}

export interface ApiError {
  detail: string;
  status: number;
}
