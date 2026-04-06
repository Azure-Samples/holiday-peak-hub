import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { AdminServiceDashboardPage } from '@/components/admin/AdminServiceDashboardPage';
import agentApiClient from '@/lib/api/agentClient';
import { useAdminServiceDashboard } from '@/lib/hooks/useAdminServiceDashboard';

jest.mock('@/lib/api/agentClient', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

jest.mock('@/lib/hooks/useAdminServiceDashboard', () => ({
  DEFAULT_ADMIN_SERVICE_RANGE: '1h',
  ADMIN_SERVICE_RANGE_OPTIONS: [{ value: '1h', label: 'Last 1 hour' }],
  useAdminServiceDashboard: jest.fn(),
}));

jest.mock('@/components/templates/MainLayout', () => ({
  MainLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock('@/components/molecules/Card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock('@/components/atoms/Badge', () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));

jest.mock('@/components/atoms/Select', () => ({
  Select: ({
    value,
    onChange,
    options,
    ariaLabel,
    name,
  }: {
    value: string;
    onChange: (event: React.ChangeEvent<HTMLSelectElement>) => void;
    options: Array<{ value: string; label: string }>;
    ariaLabel?: string;
    name?: string;
  }) => (
    <select aria-label={ariaLabel} name={name} value={value} onChange={onChange}>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  ),
}));

jest.mock('@/components/atoms/Button', () => ({
  Button: ({
    children,
    onClick,
    disabled,
    ariaLabel,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    ariaLabel?: string;
  }) => (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={ariaLabel}>
      {children}
    </button>
  ),
}));

const mockUseAdminServiceDashboard = useAdminServiceDashboard as jest.Mock;
const mockAgentPost = agentApiClient.post as jest.Mock;

describe('AdminServiceDashboardPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    mockUseAdminServiceDashboard.mockReturnValue({
      data: {
        domain: 'ecommerce',
        service: 'catalog',
        agent_service: 'ecommerce-catalog-search',
        generated_at: '2026-04-05T12:00:00Z',
        tracing_enabled: true,
        status_cards: [],
        activity: [],
        model_usage: [],
      },
      isLoading: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: jest.fn(),
    });
  });

  it('uses intelligent as default mode for catalog admin invoke calls with scoped timeout', async () => {
    mockAgentPost.mockResolvedValue({ data: { summary: 'ok' } });

    render(<AdminServiceDashboardPage domain="ecommerce" service="catalog" />);

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'find running shoes' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Run agent' }));

    await waitFor(() => {
      expect(mockAgentPost).toHaveBeenCalledTimes(1);
    });

    expect(mockAgentPost).toHaveBeenCalledWith(
      '/ecommerce-catalog-search/invoke',
      {
        intent: 'default',
        payload: expect.objectContaining({
          source: 'admin_dashboard',
          domain: 'ecommerce',
          service: 'catalog',
          query: 'find running shoes',
          prompt: 'find running shoes',
          mode: 'intelligent',
        }),
      },
      {
        timeout: 60_000,
      },
    );
  });

  it('preserves explicit mode override from JSON input for catalog admin invoke calls', async () => {
    mockAgentPost.mockResolvedValue({ data: { summary: 'ok' } });

    render(<AdminServiceDashboardPage domain="ecommerce" service="catalog" />);

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: '{"query":"find boots","mode":"keyword"}' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Run agent' }));

    await waitFor(() => {
      expect(mockAgentPost).toHaveBeenCalledTimes(1);
    });

    expect(mockAgentPost).toHaveBeenCalledWith(
      '/ecommerce-catalog-search/invoke',
      {
        intent: 'default',
        payload: expect.objectContaining({
          source: 'admin_dashboard',
          domain: 'ecommerce',
          service: 'catalog',
          query: 'find boots',
          prompt: 'find boots',
          mode: 'keyword',
        }),
      },
      {
        timeout: 60_000,
      },
    );
  });
});
