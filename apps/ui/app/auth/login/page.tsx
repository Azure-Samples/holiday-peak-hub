'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { Button } from '@/components/atoms/Button';
import { Card } from '@/components/molecules/Card';
import { FiShoppingBag } from 'react-icons/fi';
import { useAuth } from '@/contexts/AuthContext';
import { isDevAuthMockUiEnabled } from '@/lib/auth/msalConfig';

function resolvePostLoginPath(rawRedirectPath: string | null): string {
  if (!rawRedirectPath) {
    return '/';
  }

  if (!rawRedirectPath.startsWith('/') || rawRedirectPath.startsWith('//')) {
    return '/';
  }

  return rawRedirectPath;
}

export default function LoginPage() {
  const router = useRouter();
  const { login, loginAsMockRole, isAuthenticated, isLoading, authConfigError } = useAuth();
  const searchParams = useSearchParams();
  const [loginError, setLoginError] = React.useState<string | null>(null);
  const [isMockLoading, setIsMockLoading] = React.useState(false);
  const [selectedMockRole, setSelectedMockRole] = React.useState<
    'customer' | 'staff' | 'admin' | null
  >(null);
  const redirectPath = searchParams.get('redirect');
  const postLoginPath = React.useMemo(
    () => resolvePostLoginPath(redirectPath),
    [redirectPath]
  );
  const hasRouteProtectionRedirect = Boolean(
    redirectPath && redirectPath.startsWith('/')
  );
  const isMockModeEnabled = isDevAuthMockUiEnabled;

  const mockRoleLabels: Record<'customer' | 'staff' | 'admin', string> = {
    customer: 'Customer',
    staff: 'Staff',
    admin: 'Admin',
  };

  const handleMicrosoftLogin = async () => {
    try {
      setLoginError(null);
      await login();
    } catch {
      setLoginError("Couldn't proceed with your login. Please try again later.");
    }
  };

  const handleMockLogin = async (role: 'customer' | 'staff' | 'admin') => {
    try {
      setLoginError(null);
      setIsMockLoading(true);
      setSelectedMockRole(role);
      await loginAsMockRole(role);
      router.replace(postLoginPath);
    } catch {
      setLoginError("Couldn't proceed with your login. Please try again later.");
    } finally {
      setIsMockLoading(false);
      setSelectedMockRole(null);
    }
  };

  React.useEffect(() => {
    if (authConfigError) {
      setLoginError("Couldn't proceed with your login. Please try again later.");
    }
  }, [authConfigError]);

  React.useEffect(() => {
    if (isAuthenticated && !isLoading) {
      router.replace(postLoginPath);
    }
  }, [isAuthenticated, isLoading, postLoginPath, router]);

  return (
    <MainLayout>
      <div className="max-w-md mx-auto py-12">
        {isAuthenticated && !isLoading && (
          <div
            role="status"
            aria-live="polite"
            className="mb-4 rounded-md border border-cyan-200 bg-cyan-50 px-3 py-2 text-sm text-cyan-800 dark:border-cyan-800 dark:bg-cyan-950 dark:text-cyan-200"
          >
            Finishing sign-in and redirecting…
          </div>
        )}

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-ocean-100 dark:bg-ocean-900 rounded-full mb-4">
            <svg className="w-8 h-8 text-ocean-500 dark:text-ocean-300" viewBox="0 0 23 23" fill="none">
              <rect width="11" height="11" fill="currentColor" />
              <rect x="12" width="11" height="11" fill="currentColor" opacity="0.8" />
              <rect y="12" width="11" height="11" fill="currentColor" opacity="0.8" />
              <rect x="12" y="12" width="11" height="11" fill="currentColor" opacity="0.6" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Welcome to Holiday Peak Hub
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {isMockModeEnabled
              ? 'Choose a demo role or sign in with Microsoft.'
              : 'Sign in with Microsoft to continue.'}
          </p>
        </div>

        {isMockModeEnabled && (
          <Card className="p-6 mb-6">
            <h2 id="mock-login-title" className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              Development Mock Login
            </h2>
            <p id="mock-login-description" className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Use these quick buttons to simulate Customer, Staff, or Admin roles for demo flows.
            </p>
            <p id="mock-login-status" role="status" aria-live="polite" className="text-xs text-gray-500 dark:text-gray-400 mb-4">
              {isMockLoading && selectedMockRole
                ? `Signing in as ${mockRoleLabels[selectedMockRole]}…`
                : isLoading
                  ? 'Mock role actions are disabled while Microsoft sign-in is in progress.'
                  : 'Select a role to simulate authentication.'}
            </p>
            <fieldset aria-labelledby="mock-login-title" aria-describedby="mock-login-description mock-login-status">
              <legend className="sr-only">Select a development role</legend>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Button
                  onClick={() => handleMockLogin('customer')}
                  variant="outline"
                  disabled={isMockLoading || isLoading}
                  ariaLabel="Sign in as Customer in development mock mode"
                  aria-pressed={selectedMockRole === 'customer'}
                >
                  {isMockLoading && selectedMockRole === 'customer'
                    ? 'Signing in as Customer…'
                    : 'Sign in as Customer'}
                </Button>
                <Button
                  onClick={() => handleMockLogin('staff')}
                  variant="outline"
                  disabled={isMockLoading || isLoading}
                  ariaLabel="Sign in as Staff in development mock mode"
                  aria-pressed={selectedMockRole === 'staff'}
                >
                  {isMockLoading && selectedMockRole === 'staff'
                    ? 'Signing in as Staff…'
                    : 'Sign in as Staff'}
                </Button>
                <Button
                  onClick={() => handleMockLogin('admin')}
                  variant="outline"
                  disabled={isMockLoading || isLoading}
                  ariaLabel="Sign in as Admin in development mock mode"
                  aria-pressed={selectedMockRole === 'admin'}
                >
                  {isMockLoading && selectedMockRole === 'admin'
                    ? 'Signing in as Admin…'
                    : 'Sign in as Admin'}
                </Button>
              </div>
            </fieldset>
          </Card>
        )}

        {/* Sign in with Microsoft */}
        <Card className="p-8 mb-6">
          {hasRouteProtectionRedirect && !loginError && (
            <div
              role="status"
              aria-live="polite"
              className="mb-4 rounded-md border border-cyan-200 bg-cyan-50 px-3 py-2 text-sm text-cyan-800 dark:border-cyan-800 dark:bg-cyan-950 dark:text-cyan-200"
            >
              Sign in to continue to the page you requested.
            </div>
          )}

          <Button
            onClick={handleMicrosoftLogin}
            size="lg"
            className="w-full bg-hp-neutral-700 hover:bg-hp-neutral-800 dark:bg-white dark:hover:bg-gray-100 text-white dark:text-gray-900 flex items-center justify-center gap-3"
            disabled={isLoading || Boolean(authConfigError)}
          >
            <svg className="w-5 h-5" viewBox="0 0 23 23" fill="none">
              <rect width="11" height="11" fill="#F25022" />
              <rect x="12" width="11" height="11" fill="#7FBA00" />
              <rect y="12" width="11" height="11" fill="#00A4EF" />
              <rect x="12" y="12" width="11" height="11" fill="#FFB900" />
            </svg>
            {isLoading ? 'Signing in…' : 'Sign in with Microsoft'}
          </Button>

          {loginError && (
            <div
              role="alert"
              aria-live="assertive"
              className="mt-4 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
            >
              {loginError}
            </div>
          )}

          <p className="mt-4 text-xs text-center text-gray-500 dark:text-gray-400">
            Authentication is managed by Microsoft Entra ID.
            <br />
            Your credentials are never stored by this application.
          </p>
        </Card>

        {/* Guest Checkout */}
        <div className="mt-8">
          <Card className="p-6 bg-gradient-to-r from-cyan-50 to-ocean-50 dark:from-cyan-950 dark:to-ocean-950 border-cyan-200 dark:border-cyan-800">
            <div className="flex items-center gap-4">
              <FiShoppingBag className="w-8 h-8 text-cyan-500 dark:text-cyan-300 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                  Continue as Guest
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Browse products without signing in
                </p>
                <Link href="/">
                  <Button variant="outline" size="sm" className="border-cyan-500 text-cyan-500 hover:bg-cyan-50 dark:border-cyan-300 dark:text-cyan-300">
                    Browse Products
                  </Button>
                </Link>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
