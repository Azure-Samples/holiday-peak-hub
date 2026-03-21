import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import LoginPage from '../../app/auth/login/page';

const replaceMock = jest.fn();
const useSearchParamsMock = jest.fn(() => ({ get: (_key: string) => null as string | null }));
const useAuthMock = jest.fn();

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
  isDevAuthMockUiEnabled: false,
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
});
