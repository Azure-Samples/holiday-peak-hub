'use client';

import React from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Button } from '@/components/atoms/Button';
import { Card } from '@/components/molecules/Card';
import { FiShoppingBag } from 'react-icons/fi';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginPage() {
  const { login, isAuthenticated, isLoading, authConfigError } = useAuth();
  const [loginError, setLoginError] = React.useState<string | null>(null);

  const handleMicrosoftLogin = async () => {
    try {
      setLoginError(null);
      await login();
    } catch {
      setLoginError("Couldn't proceed with your login. Please try again later.");
    }
  };

  React.useEffect(() => {
    if (authConfigError) {
      setLoginError("Couldn't proceed with your login. Please try again later.");
    }
  }, [authConfigError]);

  // If already authenticated, redirect
  if (isAuthenticated && !isLoading) {
    if (typeof window !== 'undefined') {
      window.location.href = '/';
    }
    return null;
  }

  return (
    <MainLayout>
      <div className="max-w-md mx-auto py-12">
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
            Sign in with your Microsoft account to continue
          </p>
        </div>

        {/* Sign in with Microsoft */}
        <Card className="p-8 mb-6">
          <Button
            onClick={handleMicrosoftLogin}
            size="lg"
            className="w-full bg-[#2F2F2F] hover:bg-[#1a1a1a] dark:bg-white dark:hover:bg-gray-100 text-white dark:text-gray-900 flex items-center justify-center gap-3"
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
            <div className="mt-4 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
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
