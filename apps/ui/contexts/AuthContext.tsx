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
import { getMsalConfig, loginRequest, apiRequest } from '../lib/auth/msalConfig';
import { authService } from '../lib/services/authService';
import type { User } from '../lib/types/api';

interface AuthContextType {
  user: User | null;
  account: AccountInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Auth Provider Component (inner - uses MSAL hooks)
 */
function AuthProviderInner({ children }: { children: ReactNode }) {
  const { instance, accounts, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const account = accounts[0] || null;

  /**
   * Get access token for API calls
   */
  const getAccessToken = async (): Promise<string | null> => {
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
   * Login handler
   */
  const login = async () => {
    try {
      await instance.loginPopup(loginRequest);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  /**
   * Logout handler
   */
  const logout = async () => {
    try {
      // Clear backend session
      await authService.logout();
      
      // Clear MSAL session
      await instance.logoutPopup({
        account: account,
      });
      
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
      throw error;
    }
  };

  /**
   * Load user profile when authenticated
   */
  useEffect(() => {
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
          }
        } catch (error) {
          console.error('Failed to load user:', error);
          setUser(null);
        } finally {
          setIsLoading(false);
        }
      } else {
        setIsLoading(false);
      }
    };

    loadUser();
  }, [isAuthenticated, account, inProgress]);

  const value: AuthContextType = {
    user,
    account,
    isAuthenticated,
    isLoading: isLoading || inProgress !== InteractionStatus.None,
    login,
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
  const [msalInstance, setMsalInstance] = useState<PublicClientApplication | null>(
    null
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const instance = new PublicClientApplication(getMsalConfig());
    setMsalInstance(instance);
  }, []);

  if (!msalInstance) {
    return (
      <AuthContext.Provider
        value={{
          user: null,
          account: null,
          isAuthenticated: false,
          isLoading: true,
          login: async () => {},
          logout: async () => {},
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
