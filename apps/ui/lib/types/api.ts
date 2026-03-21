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

export interface CatalogProductContract {
  sku: string;
  name: string;
  description: string;
  category_id: string;
  price: number;
  currency: 'usd';
  in_stock: boolean;
}

export interface CustomerProfileContract {
  customer_id: string;
  email?: string | null;
  name?: string | null;
  phone?: string | null;
  tier: string;
  crm_profile?: Record<string, unknown> | null;
  personalization?: Record<string, unknown> | null;
}

export interface PricingOffer {
  code: string;
  title: string;
  amount: number;
  offer_type: 'bulk' | 'loyalty' | 'dynamic';
  source: 'rule' | 'agent';
}

export interface PricingOffersRequest {
  customer_id: string;
  sku: string;
  quantity: number;
  currency?: 'usd';
}

export interface PricingOffersResponse {
  customer_id: string;
  sku: string;
  quantity: number;
  currency: 'usd';
  base_price: number;
  offers: PricingOffer[];
  final_price: number;
}

export interface RecommendationCandidate {
  sku: string;
  score: number;
}

export interface RankRecommendationsRequest {
  customer_id: string;
  candidates: RecommendationCandidate[];
}

export interface RankedRecommendation {
  sku: string;
  score: number;
  reason_codes: string[];
}

export interface RankRecommendationsResponse {
  customer_id: string;
  ranked: RankedRecommendation[];
}

export interface ComposeRecommendationsRequest {
  customer_id: string;
  ranked_items: RecommendationCandidate[];
  max_items?: number;
}

export interface ComposedRecommendation {
  sku: string;
  title: string;
  score: number;
  message: string;
}

export interface ComposeRecommendationsResponse {
  customer_id: string;
  headline: string;
  recommendations: ComposedRecommendation[];
}

// Product types
export interface Product {
  id: string;
  name: string;
  description: string;
  enriched_description?: string;
  price: number;
  category_id: string;
  image_url?: string;
  in_stock: boolean;
  rating?: number;
  review_count?: number;
  features?: string[];
  use_cases?: string[];
  complementary_products?: string[];
  substitute_products?: string[];
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

export type InventoryHealthStatus = 'healthy' | 'low_stock' | 'out_of_stock';

export interface InventoryItem {
  id: string;
  sku: string;
  quantity_on_hand: number;
  reserved_quantity: number;
  available_quantity: number;
  reorder_point: number;
  safety_stock: number;
  low_stock: boolean;
  health_status: InventoryHealthStatus;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
  audit_log: Array<Record<string, unknown>>;
}

export interface InventoryHealthResponse {
  total_skus: number;
  healthy: number;
  low_stock: number;
  out_of_stock: number;
  items: InventoryItem[];
}

export type ReservationStatus = 'created' | 'confirmed' | 'released';

export interface CreateReservationRequest {
  sku: string;
  quantity: number;
  reason?: string;
}

export interface ReservationActionRequest {
  reason?: string;
}

export interface InventoryReservation {
  id: string;
  sku: string;
  quantity: number;
  status: ReservationStatus;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
  confirmed_at?: string | null;
  confirmed_by?: string | null;
  released_at?: string | null;
  released_by?: string | null;
  reason?: string | null;
  status_history: Array<Record<string, unknown>>;
  audit_log: Array<Record<string, unknown>>;
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

export interface ConfirmPaymentIntentRequest {
  order_id: string;
  payment_intent_id: string;
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
  top_products: Array<Record<string, unknown>>;
}

export type TicketStatus = 'open' | 'in_progress' | 'pending_customer' | 'escalated' | 'resolved' | 'closed';
export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface Ticket {
  id: string;
  user_id: string;
  subject: string;
  status: TicketStatus;
  priority: TicketPriority;
  created_at: string;
  description?: string;
  assignee_id?: string;
  updated_at?: string;
  updated_by?: string;
  resolved_at?: string;
  resolved_by?: string;
  escalation_reason?: string;
  escalated_at?: string;
  escalated_by?: string;
  resolution_note?: string;
  status_history?: Array<{
    from?: string | null;
    to: string;
    at: string;
    actor_id: string;
    reason?: string | null;
  }>;
  audit_log?: Array<{
    action: string;
    at: string;
    actor_id: string;
    actor_roles: string[];
    reason?: string;
    details?: Record<string, unknown>;
  }>;
}

export interface CreateTicketRequest {
  user_id: string;
  subject: string;
  priority?: TicketPriority;
  description?: string;
}

export interface UpdateTicketRequest {
  subject?: string;
  priority?: TicketPriority;
  status?: TicketStatus;
  assignee_id?: string;
  reason?: string;
  note?: string;
}

export interface ResolveTicketRequest {
  reason?: string;
  resolution_note?: string;
}

export interface EscalateTicketRequest {
  reason: string;
}

export type ReturnStatus = 'requested' | 'approved' | 'rejected' | 'received' | 'restocked' | 'refunded';
export type RefundStatus = 'issued';

export interface ReturnStatusHistoryItem {
  from?: string | null;
  to: ReturnStatus;
  at: string;
  actor_id: string;
  actor_roles: string[];
  reason?: string | null;
}

export interface ReturnAuditLogItem {
  action: string;
  at: string;
  actor_id: string;
  actor_roles: string[];
  reason?: string;
}

export interface RefundStatusHistoryItem {
  from?: string | null;
  to: RefundStatus;
  at: string;
  actor_id: string;
  actor_roles: string[];
}

export interface RefundAuditLogItem {
  action: string;
  at: string;
  actor_id: string;
  actor_roles: string[];
}

export interface Refund {
  id: string;
  return_id: string;
  order_id: string;
  user_id: string;
  status: RefundStatus;
  created_at: string;
  updated_at: string;
  issued_at: string;
  last_transition_at: string;
  requested_at: string;
  status_history: RefundStatusHistoryItem[];
  audit_log: RefundAuditLogItem[];
}

export interface Return {
  id: string;
  order_id: string;
  user_id: string;
  status: ReturnStatus;
  reason: string;
  items: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
  requested_at: string;
  approved_at?: string | null;
  rejected_at?: string | null;
  received_at?: string | null;
  restocked_at?: string | null;
  refunded_at?: string | null;
  last_transition_at: string;
  status_history: ReturnStatusHistoryItem[];
  audit_log: ReturnAuditLogItem[];
  refund?: Refund | null;
  idempotent?: boolean;
}

export interface CreateReturnRequest {
  order_id: string;
  reason: string;
  items?: Array<Record<string, unknown>>;
}

export interface ReturnTransitionRequest {
  reason?: string;
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
  source_type?: string;
  evidence: string[];
  image_evidence?: string[];
  source_assets?: string[];
  reasoning?: string;
  intent?: string;
  intent_confidence?: number;
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

export type EnrichmentJobStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'completed'
  | 'approved'
  | 'rejected'
  | 'failed';

export interface EnrichmentMonitorStatusCard {
  label: string;
  value: number;
  trend?: 'up' | 'down' | 'neutral';
}

export interface EnrichmentActiveJob {
  id: string;
  entity_id: string;
  status: EnrichmentJobStatus;
  source_type: string;
  confidence: number;
  updated_at: string;
}

export interface EnrichmentErrorLogItem {
  id: string;
  entity_id?: string;
  message: string;
  timestamp: string;
}

export interface EnrichmentThroughput {
  per_minute: number;
  last_10m: number;
  failed_last_10m: number;
}

export interface EnrichmentMonitorDashboard {
  status_cards: EnrichmentMonitorStatusCard[];
  active_jobs: EnrichmentActiveJob[];
  error_log: EnrichmentErrorLogItem[];
  throughput: EnrichmentThroughput;
}

export interface EnrichmentAttributeDiff {
  field_name: string;
  original_value: string | null;
  enriched_value: string;
  confidence: number;
  source_type: string;
  intent?: string;
  intent_confidence?: number;
  reasoning?: string;
}

export interface EnrichmentEntityDetail {
  entity_id: string;
  title: string;
  status: EnrichmentJobStatus;
  confidence: number;
  trace_id?: string;
  source_assets: string[];
  image_evidence: string[];
  reasoning: string;
  diffs: EnrichmentAttributeDiff[];
}

export interface EnrichmentDecisionRequest {
  action: 'approve' | 'reject';
}

export type AgentHealthStatus = 'healthy' | 'degraded' | 'down' | 'unknown';
export type AgentTraceStatus = 'ok' | 'warning' | 'error' | 'unknown';
export type AgentModelTier = 'slm' | 'llm' | 'unknown';
export type AgentMonitorTimeRange = '15m' | '1h' | '6h' | '24h' | '7d';

export interface AgentHealthCardMetric {
  id: string;
  label: string;
  status: AgentHealthStatus;
  latency_ms: number;
  error_rate: number;
  throughput_rpm: number;
  updated_at: string;
}

export interface AgentTraceSummary {
  trace_id: string;
  agent_name: string;
  operation: string;
  status: AgentTraceStatus;
  started_at: string;
  duration_ms: number;
  model_tier: AgentModelTier;
  error_count: number;
}

export interface AgentTraceSpan {
  span_id: string;
  parent_span_id?: string | null;
  name: string;
  service: string;
  status: AgentTraceStatus;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  model_tier?: AgentModelTier;
  error_message?: string;
  tool_name?: string;
  tool_input?: string;
  tool_output?: string;
  model_name?: string;
  prompt_excerpt?: string;
  completion_excerpt?: string;
  decision_outcome?: string;
  confidence_score?: number;
}

export interface AgentTraceToolCall {
  span_id: string;
  tool_name: string;
  input?: string;
  output?: string;
  status?: AgentTraceStatus;
}

export interface AgentTraceModelInvocation {
  span_id: string;
  model_name: string;
  model_tier: AgentModelTier;
  prompt_excerpt?: string;
  completion_excerpt?: string;
  input_tokens?: number;
  output_tokens?: number;
  latency_ms?: number;
  cost_usd?: number;
}

export interface AgentModelUsageRow {
  model_name: string;
  model_tier: AgentModelTier;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  avg_latency_ms: number;
  cost_usd: number;
}

export interface AgentMonitorDashboard {
  tracing_enabled: boolean;
  generated_at: string;
  health_cards: AgentHealthCardMetric[];
  trace_feed: AgentTraceSummary[];
  model_usage: AgentModelUsageRow[];
}

export interface AgentTraceDetail {
  tracing_enabled: boolean;
  trace_id: string;
  root_agent_name: string;
  status: AgentTraceStatus;
  started_at: string;
  duration_ms: number;
  spans: AgentTraceSpan[];
  tool_calls?: AgentTraceToolCall[];
  model_invocations?: AgentTraceModelInvocation[];
  decision_outcome?: string;
  decision_confidence?: number;
}

export interface AgentEvaluationTrend {
  metric: string;
  latest: number;
  change_pct: number;
  points: Array<{
    timestamp: string;
    value: number;
  }>;
}

export interface AgentEvaluationComparisonRow {
  model_name: string;
  model_tier: AgentModelTier;
  dataset: string;
  score: number;
  pass_rate: number;
  avg_latency_ms: number;
  cost_per_1k_tokens: number;
}

export interface AgentEvaluationSummary {
  overall_score: number;
  pass_rate: number;
  total_runs: number;
}

export interface AgentEvaluationsPayload {
  tracing_enabled: boolean;
  generated_at: string;
  summary: AgentEvaluationSummary;
  trends: AgentEvaluationTrend[];
  comparison: AgentEvaluationComparisonRow[];
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
