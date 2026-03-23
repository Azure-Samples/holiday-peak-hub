import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import LoginPage from '../../app/auth/login/page';

const replaceMock = jest.fn();
const useSearchParamsMock = jest.fn(() => ({ get: (_key: string) => null as string | null }));
const useAuthMock = jest.fn();
const mockUiState = { enabled: false };

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    replace: replaceMock,
    push: jest.fn(),
  }),
  useSearchParams: () => useSearchParamsMock(),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}));

jest.mock('../../lib/auth/msalConfig', () => ({
  get isDevAuthMockUiEnabled() {
    return mockUiState.enabled;
  },
}));

jest.mock('@/components/templates/MainLayout', () => ({
  MainLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="main-layout">{children}</div>
  ),
}));

jest.mock('@/components/atoms/Button', () => ({
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button {...props}>{children}</button>
  ),
}));

jest.mock('@/components/molecules/Card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe('login post-auth redirect behavior', () => {
  beforeEach(() => {
    replaceMock.mockClear();
    mockUiState.enabled = false;
    useSearchParamsMock.mockReturnValue({
      get: (_key: string) => null,
    });

    useAuthMock.mockReturnValue({
      login: jest.fn(),
      loginAsMockRole: jest.fn(),
      isAuthenticated: false,
      isLoading: false,
      authConfigError: null,
    });
  });

  it('redirects authenticated users to redirect target and keeps non-blank transition state', async () => {
    useSearchParamsMock.mockReturnValue({
      get: (key: string) => (key === 'redirect' ? '/admin' : null),
    });
    useAuthMock.mockReturnValue({
      login: jest.fn(),
      loginAsMockRole: jest.fn(),
      isAuthenticated: true,
      isLoading: false,
      authConfigError: null,
    });

    render(<LoginPage />);

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith('/admin');
    });
    expect(screen.getByText('Finishing sign-in and redirecting…')).toBeInTheDocument();
  });

  it('falls back to root when redirect target is unsafe', async () => {
    useSearchParamsMock.mockReturnValue({
      get: (key: string) => (key === 'redirect' ? 'https://evil.example' : null),
    });
    useAuthMock.mockReturnValue({
      login: jest.fn(),
      loginAsMockRole: jest.fn(),
      isAuthenticated: true,
      isLoading: false,
      authConfigError: null,
    });

    render(<LoginPage />);

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith('/');
    });
  });

  it('prioritizes mock role controls before Microsoft sign-in in mock-enabled mode', () => {
    mockUiState.enabled = true;

    render(<LoginPage />);

    const roleButtons = screen.getAllByRole('button', { name: /Sign in as/i });
    const microsoftButton = screen.getByRole('button', { name: 'Sign in with Microsoft' });
    const allButtons = screen.getAllByRole('button');
    const firstRoleButtonIndex = allButtons.findIndex((button) => button.textContent?.includes('Sign in as'));
    const microsoftButtonIndex = allButtons.indexOf(microsoftButton);

    expect(roleButtons.length).toBe(3);
    expect(firstRoleButtonIndex).toBeGreaterThanOrEqual(0);
    expect(microsoftButtonIndex).toBeGreaterThanOrEqual(0);
    expect(firstRoleButtonIndex).toBeLessThan(microsoftButtonIndex);
    expect(microsoftButton).toBeInTheDocument();
  });

  it('keeps Microsoft sign-in primary and hides mock role controls when mock mode is disabled', () => {
    mockUiState.enabled = false;

    render(<LoginPage />);

    expect(screen.getByRole('button', { name: 'Sign in with Microsoft' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Sign in as/i })).not.toBeInTheDocument();
  });
});
