"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { FiLogIn, FiLogOut, FiMenu, FiX } from "react-icons/fi";

import { useAuth } from "@/contexts/AuthContext";
import { isDevAuthMockUiEnabled } from "@/lib/auth/msalConfig";

export default function Navbar1() {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, logout, loginAsMockRole } = useAuth();
  const [isSigningOff, setIsSigningOff] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const closeMobileMenu = useCallback(() => {
    setMobileMenuOpen(false);
  }, []);

  const toggleMobileMenu = useCallback(() => {
    setMobileMenuOpen((current) => !current);
  }, []);

  useEffect(() => {
    closeMobileMenu();
  }, [closeMobileMenu, pathname]);

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1024px)');
    const handleBreakpointChange = (event: MediaQueryListEvent) => {
      if (event.matches) {
        closeMobileMenu();
      }
    };

    media.addEventListener('change', handleBreakpointChange);
    return () => media.removeEventListener('change', handleBreakpointChange);
  }, [closeMobileMenu]);

  useEffect(() => {
    if (!mobileMenuOpen) {
      return undefined;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeMobileMenu();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [closeMobileMenu, mobileMenuOpen]);

  const handleSignOff = async () => {
    try {
      setIsSigningOff(true);
      await logout();
      router.push('/auth/login');
      router.refresh();
    } catch (error) {
      console.error('Sign off failed:', error);
    } finally {
      setIsSigningOff(false);
    }
  };

  const showMockRoleQuickLogin = isDevAuthMockUiEnabled && !isAuthenticated;

  const handleMockRoleLogin = async (role: 'customer' | 'staff' | 'admin') => {
    try {
      await loginAsMockRole(role);
      setMobileMenuOpen(false);
    } catch (error) {
      console.error('Mock role login failed:', error);
    }
  };

  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-900">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleMobileMenu}
            className="relative z-50 inline-flex items-center justify-center rounded-md border border-gray-300 bg-white/95 p-2 text-gray-900 shadow-sm hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-900/95 dark:text-white dark:hover:bg-gray-800 lg:hidden"
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileMenuOpen}
            aria-controls="primary-mobile-menu"
          >
            {mobileMenuOpen ? <FiX className="h-4 w-4" /> : <FiMenu className="h-4 w-4" />}
          </button>

          <Link href="/" className="text-sm font-semibold text-gray-900 dark:text-white">
            Holiday Peak Hub
          </Link>

          <nav className="ml-4 hidden items-center gap-1 lg:flex">
            <Link href="/dashboard" className="rounded-md px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800">
              Dashboard
            </Link>
            <Link href="/search" className="rounded-md px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800">
              Search Demo
            </Link>
            <Link href="/product?id=prd_001" className="rounded-md px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800">
              Product Demo
            </Link>
            <Link href="/search?agentChat=1" className="rounded-md px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800">
              Agent Popup
            </Link>
          </nav>
        </div>
        {isAuthenticated ? (
          <button
            type="button"
            onClick={handleSignOff}
            disabled={isLoading || isSigningOff}
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
            aria-label="Sign off"
          >
            <FiLogOut className="h-4 w-4" />
            {isSigningOff ? 'Signing off…' : 'Sign off'}
          </button>
        ) : (
          <div className="flex items-center gap-2">
            {showMockRoleQuickLogin ? (
              <div className="hidden items-center gap-1 md:flex">
                <button
                  type="button"
                  onClick={() => void handleMockRoleLogin('customer')}
                  className="rounded-md border border-gray-300 px-2 py-1 text-[11px] font-semibold text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                >
                  Customer
                </button>
                <button
                  type="button"
                  onClick={() => void handleMockRoleLogin('staff')}
                  className="rounded-md border border-gray-300 px-2 py-1 text-[11px] font-semibold text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                >
                  Staff
                </button>
                <button
                  type="button"
                  onClick={() => void handleMockRoleLogin('admin')}
                  className="rounded-md border border-gray-300 px-2 py-1 text-[11px] font-semibold text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                >
                  Admin
                </button>
              </div>
            ) : null}
            <Link
              href="/auth/login"
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
              aria-label="Sign in"
            >
              <FiLogIn className="h-4 w-4" />
              Sign in
            </Link>
          </div>
        )}
      </div>

      {mobileMenuOpen && (
        <div
          id="primary-mobile-menu"
          className="relative z-40 mt-3 space-y-1 rounded-md border border-gray-200 bg-white p-2 shadow-lg dark:border-gray-700 dark:bg-gray-900 lg:hidden"
        >
          <Link
            href="/"
            className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={closeMobileMenu}
          >
            Home
          </Link>
          <Link
            href="/dashboard"
            className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={closeMobileMenu}
          >
            Dashboard
          </Link>
          <Link
            href="/admin"
            className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={closeMobileMenu}
          >
            Admin
          </Link>
          <Link
            href="/search"
            className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={closeMobileMenu}
          >
            Search Demo
          </Link>
          <Link
            href="/product?id=prd_001"
            className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={closeMobileMenu}
          >
            Product Demo
          </Link>
          <Link
            href="/search?agentChat=1"
            className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={closeMobileMenu}
          >
            Open Agent Popup
          </Link>

          {showMockRoleQuickLogin ? (
            <div className="grid grid-cols-3 gap-2 px-1 py-2">
              <button
                type="button"
                onClick={() => void handleMockRoleLogin('customer')}
                className="rounded-md border border-gray-300 px-2 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
              >
                Customer
              </button>
              <button
                type="button"
                onClick={() => void handleMockRoleLogin('staff')}
                className="rounded-md border border-gray-300 px-2 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
              >
                Staff
              </button>
              <button
                type="button"
                onClick={() => void handleMockRoleLogin('admin')}
                className="rounded-md border border-gray-300 px-2 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
              >
                Admin
              </button>
            </div>
          ) : null}
        </div>
      )}
    </header>
  );
}
