/**
 * Truth Feature Types
 *
 * Type definitions for the truth bounded context, including review queue,
 * enrichment monitoring, schemas, and analytics.
 */

// Base truth types
export type ReviewStatus = 'pending' | 'approved' | 'rejected';

export type EnrichmentJobStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'completed'
  | 'approved'
  | 'rejected'
  | 'failed';

// Schema types
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

// Configuration types
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

// Analytics types
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

// Review queue types
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

// Enrichment monitor types
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
