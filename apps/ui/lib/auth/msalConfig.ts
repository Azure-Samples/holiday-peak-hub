/**
 * MSAL Configuration for Microsoft Entra ID authentication
 */

const entraClientId = process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID || '';
const entraTenantId = process.env.NEXT_PUBLIC_ENTRA_TENANT_ID || '';
const devAuthMockEnabled =
  process.env.NODE_ENV !== 'production' && process.env.NEXT_PUBLIC_DEV_AUTH_MOCK === 'true';

export const isEntraConfigured = Boolean(entraClientId && entraTenantId);
export const isDevAuthMockUiEnabled = devAuthMockEnabled;

export const getMissingEntraConfigKeys = (): string[] => {
  const missing: string[] = [];
  if (!entraClientId) missing.push('NEXT_PUBLIC_ENTRA_CLIENT_ID');
  if (!entraTenantId) missing.push('NEXT_PUBLIC_ENTRA_TENANT_ID');
  return missing;
};

export const getEntraConfigError = (): string | null => {
  if (isEntraConfigured || isDevAuthMockUiEnabled) {
    return null;
  }

  return "Couldn't proceed with your login.";
};

/**
 * Get MSAL configuration object (client-only)
 */
export const getMsalConfig = () => {
  const redirectUri = typeof window !== 'undefined' ? window.location.origin : '';

  return {
    auth: {
      clientId: entraClientId,
      authority: `https://login.microsoftonline.com/${entraTenantId || 'common'}`,
      redirectUri,
      postLogoutRedirectUri: redirectUri,
      navigateToLoginRequestUrl: true,
    },
    cache: {
      cacheLocation: 'sessionStorage',
      storeAuthStateInCookie: false,
    },
    system: {
      loggerOptions: {
        loggerCallback: (_level: number, message: string, containsPii: boolean) => {
          if (containsPii) return;
          console.warn(message);
        },
      },
    },
  };
};

/**
 * Scopes for login request
 */
export const loginRequest = {
  scopes: ['openid', 'profile', 'email', 'User.Read'],
};

/**
 * Scopes for API access
 */
export const apiRequest = {
  scopes: entraClientId
    ? [`api://${entraClientId}/user_impersonation`]
    : ['openid', 'profile', 'email', 'User.Read'],
};
