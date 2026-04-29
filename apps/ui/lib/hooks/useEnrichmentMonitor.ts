import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { enrichmentMonitorService } from '../services/enrichmentMonitorService';

export function useEnrichmentMonitorDashboard(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['admin', 'enrichment-monitor', 'dashboard'],
    queryFn: () => enrichmentMonitorService.getDashboard(),
    enabled: options?.enabled ?? true,
    refetchInterval: 10_000,
  });
}

export function useEnrichmentPipelineStats() {
  return useQuery({
    queryKey: ['admin', 'enrichment-monitor', 'pipeline-stats'],
    queryFn: () => enrichmentMonitorService.getEnrichmentPipelineStats(),
    refetchInterval: 30_000,
  });
}

export function useActiveEnrichmentJobs() {
  return useQuery({
    queryKey: ['admin', 'enrichment-monitor', 'active-jobs'],
    queryFn: () => enrichmentMonitorService.getActiveEnrichmentJobs(),
    refetchInterval: 10_000,
  });
}

export function useEnrichmentMonitorDetail(entityId: string) {
  return useQuery({
    queryKey: ['admin', 'enrichment-monitor', 'detail', entityId],
    queryFn: () => enrichmentMonitorService.getEntityDetail(entityId),
    enabled: Boolean(entityId),
    refetchInterval: 30_000,
  });
}

export function useEnrichmentDetail(entityId: string) {
  return useQuery({
    queryKey: ['admin', 'enrichment-monitor', 'detail-v2', entityId],
    queryFn: () => enrichmentMonitorService.getEnrichmentDetail(entityId),
    enabled: Boolean(entityId),
    refetchInterval: 30_000,
  });
}

export function useEnrichmentDecision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ entityId, action }: { entityId: string; action: 'approve' | 'reject' }) =>
      enrichmentMonitorService.submitDecision(entityId, { action }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'enrichment-monitor', 'dashboard'] });
      queryClient.invalidateQueries({
        queryKey: ['admin', 'enrichment-monitor', 'detail', variables.entityId],
      });
      queryClient.invalidateQueries({ queryKey: ['staff', 'review'] });
    },
  });
}
