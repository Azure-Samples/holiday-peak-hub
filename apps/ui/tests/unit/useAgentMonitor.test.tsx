import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { ApiError } from '../../lib/api/client';
import {
  isTracingUnavailableError,
  useAgentMonitorDashboard,
  useAgentGlobalHealth,
  useAgentTraceDetail,
} from '../../lib/hooks/useAgentMonitor';

const getDashboard = jest.fn();
const getTraceDetail = jest.fn();
const getEvaluations = jest.fn();

jest.mock('../../lib/services/agentMonitorService', () => ({
  agentMonitorService: {
    getDashboard: (...args: unknown[]) => getDashboard(...args),
    getTraceDetail: (...args: unknown[]) => getTraceDetail(...args),
    getEvaluations: (...args: unknown[]) => getEvaluations(...args),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useAgentMonitor hooks', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();

    getDashboard.mockResolvedValue({
      tracing_enabled: true,
      generated_at: '2026-03-19T11:00:00Z',
      health_cards: [
        {
          id: 'agent-a',
          label: 'Agent A',
          status: 'healthy',
          latency_ms: 120,
          error_rate: 0.01,
          throughput_rpm: 14,
          updated_at: '2026-03-19T11:00:00Z',
        },
      ],
      trace_feed: [],
      model_usage: [],
    });

    getTraceDetail.mockResolvedValue({
      tracing_enabled: true,
      trace_id: 'trace-1',
      root_agent_name: 'search-agent',
      status: 'ok',
      started_at: '2026-03-19T10:59:00Z',
      duration_ms: 180,
      spans: [],
    });

    getEvaluations.mockResolvedValue({
      tracing_enabled: true,
      generated_at: '2026-03-19T11:00:00Z',
      summary: { overall_score: 0.91, pass_rate: 0.96, total_runs: 120 },
      trends: [],
      comparison: [],
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('polls dashboard every 10 seconds', async () => {
    renderHook(() => useAgentMonitorDashboard('1h'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(getDashboard).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      jest.advanceTimersByTime(10_000);
    });

    await waitFor(() => {
      expect(getDashboard).toHaveBeenCalledTimes(2);
    });
  });

  it('loads trace detail once without polling', async () => {
    renderHook(() => useAgentTraceDetail('trace-1', '1h'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(getTraceDetail).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      jest.advanceTimersByTime(30_000);
    });

    expect(getTraceDetail).toHaveBeenCalledTimes(1);
  });

  it('derives global health state', async () => {
    const { result } = renderHook(() => useAgentGlobalHealth(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toBe('healthy');
    });
  });

  it('detects tracing unavailable errors', () => {
    expect(isTracingUnavailableError(new ApiError(503, 'Tracing service unavailable'))).toBe(true);
    expect(isTracingUnavailableError(new ApiError(404, 'Not found'))).toBe(true);
    expect(isTracingUnavailableError(new ApiError(400, 'Bad request'))).toBe(false);
  });
});
