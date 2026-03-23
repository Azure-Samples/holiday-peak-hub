'use client';

/**
 * Authentication Context
 * 
 * Provides Microsoft Entra ID authentication using MSAL
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
  PublicClientApplication,
  InteractionStatus,
  AccountInfo,
} from '@azure/msal-browser';
import { MsalProvider, useMsal, useIsAuthenticated } from '@azure/msal-react';
import {
  getMsalConfig,
  loginRequest,
  apiRequest,
  getEntraConfigError,
  getMissingEntraConfigKeys,
  isDevAuthMockUiEnabled,
  isEntraConfigured,
} from '../lib/auth/msalConfig';
import { authService } from '../lib/services/authService';
import type { User } from '../lib/types/api';
import { trackDebug } from '../lib/utils/telemetry';

interface AuthContextType {
  user: User | null;
  account: AccountInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authConfigError: string | null;
  login: () => Promise<void>;
  loginAsMockRole: (role: 'customer' | 'staff' | 'admin') => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const MOCK_AUTH_USER_STORAGE_KEY = 'mock_auth_user';

function loadPersistedMockUser(): User | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(MOCK_AUTH_USER_STORAGE_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

function persistMockUser(user: User): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(MOCK_AUTH_USER_STORAGE_KEY, JSON.stringify(user));
}

function clearPersistedMockUser(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(MOCK_AUTH_USER_STORAGE_KEY);
}

function clearLocalAuthArtifacts(): void {
  authService.clearToken();
  clearPersistedMockUser();
}

function buildMockUser(role: 'customer' | 'staff' | 'admin'): User {
  return {
    user_id: `mock-${role}`,
    name: `Mock ${role[0].toUpperCase()}${role.slice(1)}`,
    email: `mock.${role}@local.dev`,
    roles: [role],
  };
}

/**
 * Auth Provider Component (inner - uses MSAL hooks)
 */
function AuthProviderInner({ children }: { children: ReactNode }) {
  const { instance, accounts, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const [user, setUser] = useState<User | null>(null);
  const [mockUser, setMockUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const authConfigError = getEntraConfigError();

  const account = accounts[0] || null;

  /**
   * Get access token for API calls
   */
  const getAccessToken = async (): Promise<string | null> => {
    if (isDevAuthMockUiEnabled) return null;
    if (!account) return null;

    try {
      const response = await instance.acquireTokenSilent({
        ...apiRequest,
        account: account,
      });
      return response.accessToken;
    } catch (error) {
      console.error('Failed to acquire token silently:', error);
      
      // Fall back to interactive
      try {
        const response = await instance.acquireTokenPopup(apiRequest);
        return response.accessToken;
      } catch (popupError) {
        console.error('Failed to acquire token via popup:', popupError);
        return null;
      }
    }
  };

  /**
   * Synchronize server-managed signed auth cookie from a validated Entra token.
   */
  const syncAuthSessionCookie = async (token: string): Promise<void> => {
    const response = await fetch('/api/auth/session', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to synchronize auth session cookie.');
    }
  };

  /**
   * Clear server-managed auth session cookie.
   */
  const clearAuthSessionCookie = async (): Promise<void> => {
    await fetch('/api/auth/session', {
      method: 'DELETE',
    });
  };

  /**
   * Login handler
   */
  const login = async () => {
    if (isDevAuthMockUiEnabled) {
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login';
      }
      return;
    }

    if (authConfigError) {
      throw new Error(authConfigError);
    }

    try {
      await instance.loginPopup(loginRequest);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const loginAsMockRole = async (role: 'customer' | 'staff' | 'admin') => {
    if (!isDevAuthMockUiEnabled) {
      throw new Error('Mock authentication is disabled.');
    }

    const response = await fetch('/api/auth/mock/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ role }),
    });

    if (!response.ok) {
      throw new Error("Couldn't proceed with your login. Please try again later.");
    }

    const mockProfile = buildMockUser(role);
    setMockUser(mockProfile);
    setUser(mockProfile);
    persistMockUser(mockProfile);
  };

  /**
   * Logout handler
   */
  const logout = async () => {
    const finalizeLogoutState = () => {
      clearLocalAuthArtifacts();
      setMockUser(null);
      setUser(null);
    };

    if (isDevAuthMockUiEnabled) {
      try {
        await fetch('/api/auth/mock/logout', {
          method: 'POST',
        });
      } catch (error) {
        console.error('Mock logout request failed:', error);
      } finally {
        finalizeLogoutState();
      }
      return;
    }

    await Promise.allSettled([
      authService.logout(),
      clearAuthSessionCookie(),
    ]);

    finalizeLogoutState();

    try {
      await instance.logoutPopup({
        account,
      });
      return;
    } catch (popupError) {
      console.warn('MSAL popup logout failed, attempting redirect logout:', popupError);
    }

    try {
      await instance.logoutRedirect({
        account: account ?? undefined,
        postLogoutRedirectUri: '/auth/login',
      });
    } catch (redirectError) {
      console.error('MSAL redirect logout failed:', redirectError);
    }
  };

  /**
   * Load user profile when authenticated
   */
  useEffect(() => {
    if (isDevAuthMockUiEnabled) {
      setMockUser(loadPersistedMockUser());
      setIsLoading(false);
      return;
    }

    const loadUser = async () => {
      if (isAuthenticated && account && inProgress === InteractionStatus.None) {
        try {
          // Get access token
          const token = await getAccessToken();
          if (token) {
            // Store token for API calls
            authService.setToken(token);
            
            // Fetch user profile from backend
            const userProfile = await authService.getCurrentUser();
            setUser(userProfile);

            // Persist roles in a server-signed cookie for Next.js middleware route protection
            await syncAuthSessionCookie(token);
          }
        } catch (error) {
          console.error('Failed to load user:', error);
          setUser(null);
          await clearAuthSessionCookie();
        } finally {
          setIsLoading(false);
        }
      } else if (!isAuthenticated && inProgress === InteractionStatus.None) {
        await clearAuthSessionCookie();
        setIsLoading(false);
      } else {
        setIsLoading(false);
      }
    };

    loadUser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, account, inProgress]);

  const effectiveUser = isDevAuthMockUiEnabled ? mockUser : user;
  const effectiveIsAuthenticated = isDevAuthMockUiEnabled
    ? Boolean(mockUser)
    : isAuthenticated;

  const value: AuthContextType = {
    user: effectiveUser,
    account,
    isAuthenticated: effectiveIsAuthenticated,
    isLoading: isLoading || inProgress !== InteractionStatus.None,
    authConfigError,
    login,
    loginAsMockRole,
    logout,
    getAccessToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Auth Provider Component (outer - wraps with MsalProvider)
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [mockUser, setMockUser] = useState<User | null>(null);
  const [msalInstance, setMsalInstance] = useState<PublicClientApplication | null>(
    null
  );
  const [configError, setConfigError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    if (isDevAuthMockUiEnabled) {
      setMockUser(loadPersistedMockUser());
      return;
    }

    const init = async () => {
      if (!isEntraConfigured) {
        const missingKeys = getMissingEntraConfigKeys();
        trackDebug('UI running without Entra ID – authentication is disabled.', {
          missingKeys: missingKeys.join(','),
        });
        setConfigError(getEntraConfigError());
        return;
      }

      const instance = new PublicClientApplication(getMsalConfig());
      await instance.initialize();
      setMsalInstance(instance);
    };

    init().catch((err) => console.error('MSAL initialization failed:', err));
  }, []);

  if (isDevAuthMockUiEnabled) {
    return (
      <AuthContext.Provider
        value={{
          user: mockUser,
          account: null,
          isAuthenticated: Boolean(mockUser),
          isLoading: false,
          authConfigError: null,
          login: async () => {
            if (typeof window !== 'undefined') {
              window.location.href = '/auth/login';
            }
          },
          loginAsMockRole: async (role) => {
            const response = await fetch('/api/auth/mock/login', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ role }),
            });

            if (!response.ok) {
              throw new Error("Couldn't proceed with your login. Please try again later.");
            }

            const mockProfile = buildMockUser(role);
            setMockUser(mockProfile);
            persistMockUser(mockProfile);
          },
          logout: async () => {
            try {
              await fetch('/api/auth/mock/logout', {
                method: 'POST',
              });
            } catch (error) {
              console.error('Mock logout request failed:', error);
            } finally {
              clearLocalAuthArtifacts();
              setMockUser(null);
            }
          },
          getAccessToken: async () => null,
        }}
      >
        {children}
      </AuthContext.Provider>
    );
  }

  if (!msalInstance) {
    return (
      <AuthContext.Provider
        value={{
          user: null,
          account: null,
          isAuthenticated: false,
          isLoading: false,
          authConfigError: configError,
          login: async () => {
            throw new Error(configError || 'Authentication configuration is missing.');
          },
          loginAsMockRole: async () => {
            throw new Error('Mock authentication is disabled.');
          },
          logout: async () => {
            clearLocalAuthArtifacts();
          },
          getAccessToken: async () => null,
        }}
      >
        {children}
      </AuthContext.Provider>
    );
  }

  return (
    <MsalProvider instance={msalInstance}>
      <AuthProviderInner>{children}</AuthProviderInner>
    </MsalProvider>
  );
}

/**
 * Hook to use auth context
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

/**
 * HOC for protected routes
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>
): React.FC<P> {
  return function ProtectedRoute(props: P) {
    const { isAuthenticated, isLoading, login } = useAuth();

    useEffect(() => {
      if (!isLoading && !isAuthenticated) {
        login();
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isAuthenticated, isLoading]);

    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-ocean-500 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading...</p>
          </div>
        </div>
      );
    }

    if (!isAuthenticated) {
      return null;
    }

    return <Component {...props} />;
  };
}
