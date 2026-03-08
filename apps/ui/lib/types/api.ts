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
export interface CreatePaymentIntentRequest {
  order_id: string;
  amount: number;
  currency?: string;
}

export interface PaymentIntentResponse {
  client_secret: string;
  payment_intent_id: string;
  amount: number;
  currency: string;
  status: string;
}

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

// Truth Layer / HITL types
export type ReviewStatus = 'pending' | 'approved' | 'rejected';

export interface ReviewQueueItem {
  id: string;
  entity_id: string;
  product_title: string;
  category: string;
  field_name: string;
  current_value: string | null;
  proposed_value: string;
  confidence: number;
  source: string;
  proposed_at: string;
  status: ReviewStatus;
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProposedAttribute {
  id: string;
  field_name: string;
  current_value: string | null;
  proposed_value: string;
  confidence: number;
  source: string;
  evidence: string[];
  proposed_at: string;
  status: ReviewStatus;
}

export interface ProductReviewDetail {
  entity_id: string;
  product_title: string;
  category: string;
  image_url?: string;
  completeness_score: number;
  proposed_attributes: ProposedAttribute[];
}

export interface AuditEvent {
  id: string;
  entity_id: string;
  action: string;
  field_name?: string;
  old_value?: string | null;
  new_value?: string | null;
  actor: string;
  timestamp: string;
  reason?: string;
}

export interface ReviewActionRequest {
  action: 'approve' | 'reject' | 'edit';
  reason?: string;
  edited_value?: string;
}

export interface ReviewStatsResponse {
  pending: number;
  approved_today: number;
  rejected_today: number;
  avg_confidence: number;
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

// Product Truth Layer — core entity types

export interface ProductStyle {
  id: string;
  style_id: string;
  category_id: string;
  name: string;
  brand?: string;
  description?: string;
  tags: string[];
  source_system: string;
  source_id: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface ProductVariant {
  id: string;
  variant_id: string;
  style_id: string;
  category_id: string;
  sku: string;
  size?: string;
  color?: string;
  price?: number;
  currency: string;
  inventory_count: number;
  source_system: string;
  source_id: string;
  created_at: string;
  updated_at: string;
  attributes: Record<string, unknown>;
}

export interface TruthAttribute {
  id: string;
  entity_id: string;
  attribute_name: string;
  attribute_value: unknown;
  confidence: number;
  source_system: string;
  source_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'superseded';
  approved_by?: string;
  approved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface GapReport {
  id: string;
  entity_id: string;
  category_id: string;
  completeness_score: number;
  required_missing: string[];
  optional_missing: string[];
  computed_at: string;
}

export interface AssetMetadata {
  id: string;
  product_id: string;
  asset_type: string;
  url: string;
  alt_text?: string;
  width?: number;
  height?: number;
  file_size_bytes?: number;
  source_system: string;
  source_id: string;
  created_at: string;
  metadata: Record<string, unknown>;
}
