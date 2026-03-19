import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import {
  useEnrichmentMonitorDashboard,
  useEnrichmentMonitorDetail,
} from '../../lib/hooks/useEnrichmentMonitor';

const getDashboard = jest.fn();
const getEntityDetail = jest.fn();

jest.mock('../../lib/services/enrichmentMonitorService', () => ({
  enrichmentMonitorService: {
    getDashboard: (...args: unknown[]) => getDashboard(...args),
    getEntityDetail: (...args: unknown[]) => getEntityDetail(...args),
    submitDecision: jest.fn(),
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

describe('useEnrichmentMonitor hooks', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();

    getDashboard.mockResolvedValue({
      status_cards: [],
      active_jobs: [],
      error_log: [],
      throughput: { per_minute: 0, last_10m: 0, failed_last_10m: 0 },
    });

    getEntityDetail.mockResolvedValue({
      entity_id: 'prod-1',
      title: 'Sample Product',
      status: 'running',
      confidence: 0.8,
      source_assets: [],
      image_evidence: [],
      reasoning: 'Reasoning',
      diffs: [],
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('polls dashboard every 10 seconds', async () => {
    renderHook(() => useEnrichmentMonitorDashboard(), {
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

  it('polls entity detail every 30 seconds', async () => {
    renderHook(() => useEnrichmentMonitorDetail('prod-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(getEntityDetail).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      jest.advanceTimersByTime(30_000);
    });

    await waitFor(() => {
      expect(getEntityDetail).toHaveBeenCalledTimes(2);
    });
  });
});
