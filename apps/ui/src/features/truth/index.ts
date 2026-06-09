/**
 * Truth Feature - Public Facade
 *
 * This is the single public entry point for the truth bounded context.
 * All external consumers must import from this file, not from internal modules.
 *
 * Re-exports types, components, hooks, and services for truth-related functionality
 * including review queue, enrichment monitoring, schemas, and analytics.
 */

// ===== TYPES =====
export type {
  // Base types
  ReviewStatus,
  EnrichmentJobStatus,
  // Schema types
  SchemaField,
  CategorySchema,
  // Configuration types
  TenantConfig,
  // Analytics types
  TruthAnalyticsSummary,
  CompletenessBreakdown,
  PipelineThroughput,
  // Review queue types
  ReviewQueueItem,
  ReviewQueueResponse,
  ProposedAttribute,
  ProductReviewDetail,
  AuditEvent,
  ReviewActionRequest,
  ReviewStatsResponse,
  // Enrichment monitor types
  EnrichmentMonitorStatusCard,
  EnrichmentActiveJob,
  EnrichmentErrorLogItem,
  EnrichmentThroughput,
  EnrichmentMonitorDashboard,
  EnrichmentAttributeDiff,
  EnrichmentEntityDetail,
  EnrichmentDecisionRequest,
} from './types';

// ===== COMPONENTS =====
export { AuditTimeline } from './components/AuditTimeline';
export type { AuditTimelineProps } from './components/AuditTimeline';

export { CompletenessBar } from './components/CompletenessBar';
export type { CompletenessBarProps } from './components/CompletenessBar';

export { ConfidenceBadge } from '@/src/shared/components/ConfidenceBadge';
export type { ConfidenceBadgeProps } from '@/src/shared/components/ConfidenceBadge';

export { ProposalCard } from './components/ProposalCard';
export type { ProposalCardProps } from './components/ProposalCard';

export { ReviewQueueTable } from './components/ReviewQueueTable';
export type { ReviewQueueTableProps, SortKey } from './components/ReviewQueueTable';

// ===== HOOKS =====
// Truth review hooks
export {
  useReviewQueue,
  useReviewStats,
  useProductReviewDetail,
  useAuditHistory,
  useReviewAction,
} from './hooks/useTruth';

// Truth admin hooks
export {
  useTruthSchemas,
  useTruthSchema,
  useCreateTruthSchema,
  useUpdateTruthSchema,
  useDeleteTruthSchema,
  useTruthConfig,
  useUpdateTruthConfig,
  useTruthAnalyticsSummary,
  useTruthCompletenessBreakdown,
  useTruthPipelineThroughput,
} from './hooks/useTruthAdmin';

// Enrichment monitor hooks
export {
  useEnrichmentMonitorDashboard,
  useEnrichmentPipelineStats,
  useActiveEnrichmentJobs,
  useEnrichmentMonitorDetail,
  useEnrichmentDetail,
  useEnrichmentDecision,
} from './hooks/useEnrichmentMonitor';

// ===== SERVICES =====
// Truth services are exported for advanced use cases but hooks are preferred
export { truthService } from './services/truthService';
export { truthAdminService } from './services/truthAdminService';
export { enrichmentMonitorService } from './services/enrichmentMonitorService';
