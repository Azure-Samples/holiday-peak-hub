import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AgentProfileDrawer } from '@/components/demo/AgentProfileDrawer';
import { AGENT_PROFILES } from '@/lib/agents/profiles';

const useRecentTracesMock = jest.fn();

jest.mock('@/lib/services/agentStreamingService', () => ({
  __esModule: true,
  streamAgentInvocation: jest.fn(),
}));

jest.mock('@/components/organisms/AgentRobot', () => ({
  AgentRobot: ({ agentSlug }: { agentSlug: string }) => <div>{agentSlug}</div>,
}));

jest.mock('@/components/admin/TraceWaterfall', () => ({
  TraceWaterfall: () => <div>trace-waterfall</div>,
}));

jest.mock('@/lib/hooks/useAgentMonitor', () => ({
  DEFAULT_AGENT_MONITOR_RANGE: '1h',
  useRecentTraces: (...args: unknown[]) => useRecentTracesMock(...args),
  useAgentTraceDetail: () => ({ data: null, isLoading: false }),
}));

const mockStreamAgentInvocation = jest.requireMock('@/lib/services/agentStreamingService').streamAgentInvocation as jest.Mock;

describe('AgentProfileDrawer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useRecentTracesMock.mockReturnValue({ data: [] });
  });

  it('does not poll recent traces until the drawer is open for a profile', () => {
    render(
      <AgentProfileDrawer
        open={false}
        profile={null}
        liveMetrics={null}
        onClose={jest.fn()}
      />,
    );

    expect(useRecentTracesMock).toHaveBeenCalledWith(undefined, '1h', 5, {
      enabled: false,
    });
  });

  it('renders schemas and streams the curated sample payload', async () => {
    const profile = AGENT_PROFILES['ecommerce-catalog-search'];
    mockStreamAgentInvocation.mockImplementation((_slug, _payload, callbacks) => {
      callbacks.onToken?.('Matched ');
      callbacks.onToken?.('waterproof hiking boots.');
      callbacks.onDone?.({ status: 'complete' });
      return { abort: jest.fn() };
    });

    render(
      <AgentProfileDrawer
        open
        profile={profile}
        liveMetrics={null}
        onClose={jest.fn()}
      />,
    );

    expect(useRecentTracesMock).toHaveBeenCalledWith('ecommerce-catalog-search', '1h', 5, {
      enabled: true,
    });

    expect(screen.getByText('Interface Contract')).toBeInTheDocument();
    expect(screen.getByText('Mini Playground')).toBeInTheDocument();
    expect(screen.getByText('Run a sample')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Run a sample' }));

    await waitFor(() => {
      expect(mockStreamAgentInvocation).toHaveBeenCalledWith(
        'ecommerce-catalog-search',
        profile.sampleInput,
        expect.objectContaining({
          onToken: expect.any(Function),
          onResults: expect.any(Function),
          onDone: expect.any(Function),
          onError: expect.any(Function),
        }),
      );
    });

    expect(await screen.findByText('Matched waterproof hiking boots.')).toBeInTheDocument();
  });
});