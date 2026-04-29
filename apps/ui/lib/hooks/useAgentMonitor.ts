import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../api/client';
import { agentMonitorService } from '../services/agentMonitorService';
import type { AgentHealthStatus, AgentMonitorTimeRange } from '../types/api';

export const DEFAULT_AGENT_MONITOR_RANGE: AgentMonitorTimeRange = '1h';

export const AGENT_MONITOR_RANGE_OPTIONS: Array<{
  value: AgentMonitorTimeRange;
  label: string;
}> = [
  { value: '15m', label: 'Last 15 minutes' },
  { value: '1h', label: 'Last 1 hour' },
  { value: '6h', label: 'Last 6 hours' },
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
];

export function isTracingUnavailableError(error: unknown): boolean {
  if (!(error instanceof ApiError)) {
    return false;
  }

  if ([404, 501, 503].includes(error.status)) {
    return true;
  }

  const normalized = error.message.toLowerCase();
  return normalized.includes('tracing') || normalized.includes('monitor');
}

export function useAgentHealth(timeRange: AgentMonitorTimeRange) {
  return useQuery({
    queryKey: ['admin', 'agent-activity', 'health-cards', timeRange],
    queryFn: () => agentMonitorService.getAgentHealth(timeRange),
    refetchInterval: 30_000,
  });
}

export function useAgentMonitorDashboard(
  timeRange: AgentMonitorTimeRange,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ['admin', 'agent-activity', 'dashboard', timeRange],
    queryFn: () => agentMonitorService.getDashboard(timeRange),
    enabled: options?.enabled ?? true,
    refetchInterval: 10_000,
  });
}

export function useRecentTraces(
  agentName: string | undefined,
  timeRange: AgentMonitorTimeRange,
  limit = 25,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ['admin', 'agent-activity', 'recent-traces', agentName, limit, timeRange],
    queryFn: () => agentMonitorService.getRecentTraces(agentName, limit, timeRange),
    enabled: options?.enabled ?? true,
    refetchInterval: 10_000,
  });
}

export function useAgentTraceDetail(traceId: string, timeRange: AgentMonitorTimeRange) {
  return useQuery({
    queryKey: ['admin', 'agent-activity', 'trace-detail', traceId, timeRange],
    queryFn: () => agentMonitorService.getTraceDetail(traceId, timeRange),
    enabled: Boolean(traceId),
  });
}

export function useAgentEvaluations(
  timeRange: AgentMonitorTimeRange,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ['admin', 'agent-activity', 'evaluations', timeRange],
    queryFn: () => agentMonitorService.getLatestEvaluations(timeRange),
    enabled: options?.enabled ?? true,
    refetchInterval: 30_000,
  });
}

export function useModelUsageStats(
  timeRange: AgentMonitorTimeRange,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ['admin', 'agent-activity', 'model-usage', timeRange],
    queryFn: () => agentMonitorService.getModelUsageStats(timeRange),
    enabled: options?.enabled ?? true,
    refetchInterval: 30_000,
  });
}

export function useEvaluationTrends(timeRange: AgentMonitorTimeRange) {
  return useQuery({
    queryKey: ['admin', 'agent-activity', 'evaluation-trends', timeRange],
    queryFn: () => agentMonitorService.getLatestEvaluations(timeRange),
    select: (payload) => payload.trends,
    refetchInterval: 30_000,
  });
}

export function useAgentGlobalHealth(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['admin', 'agent-activity', 'global-health'],
    queryFn: () => agentMonitorService.getDashboard('15m'),
    enabled: options?.enabled ?? true,
    refetchInterval: 30_000,
    select: (dashboard): AgentHealthStatus => {
      if (!dashboard.tracing_enabled || dashboard.health_cards.length === 0) {
        return 'unknown';
      }

      if (dashboard.health_cards.some((card) => card.status === 'down')) {
        return 'down';
      }

      if (dashboard.health_cards.some((card) => card.status === 'degraded')) {
        return 'degraded';
      }

      if (dashboard.health_cards.every((card) => card.status === 'healthy')) {
        return 'healthy';
      }

      return 'unknown';
    },
  });
}
