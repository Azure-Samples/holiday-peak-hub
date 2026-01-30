/**
 * MSAL Configuration for Microsoft Entra ID authentication
 */

/**
 * Get MSAL configuration object (client-only)
 */
export const getMsalConfig = () => {
  const redirectUri = typeof window !== 'undefined' ? window.location.origin : '';

  return {
    auth: {
      clientId: process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID || '',
      authority: `https://login.microsoftonline.com/${process.env.NEXT_PUBLIC_ENTRA_TENANT_ID || 'common'}`,
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
          console.debug(message);
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
  scopes: [`api://${process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID}/user_impersonation`],
};
