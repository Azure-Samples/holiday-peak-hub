"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FiLogIn, FiLogOut, FiMenu, FiX } from "react-icons/fi";

import { useAuth } from "@/contexts/AuthContext";

export default function Navbar1() {
  const router = useRouter();
  const { isAuthenticated, isLoading, logout } = useAuth();
  const [isSigningOff, setIsSigningOff] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

  return (
    <header className="sticky top-0 z-20 border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-900">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setMobileMenuOpen((current) => !current)}
            className="inline-flex items-center justify-center rounded-md border border-gray-300 p-2 text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800 lg:hidden"
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileMenuOpen}
            aria-controls="dashboard-mobile-menu"
          >
            {mobileMenuOpen ? <FiX className="h-4 w-4" /> : <FiMenu className="h-4 w-4" />}
          </button>

          <Link href="/" className="text-sm font-semibold text-gray-900 dark:text-white">
            Holiday Peak Hub
          </Link>
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
          <Link
            href="/auth/login"
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
            aria-label="Sign in"
          >
            <FiLogIn className="h-4 w-4" />
            Sign in
          </Link>
        )}
      </div>

      {mobileMenuOpen && (
        <div
          id="dashboard-mobile-menu"
          className="mt-3 space-y-1 rounded-md border border-gray-200 bg-white p-2 dark:border-gray-700 dark:bg-gray-900 lg:hidden"
        >
          <Link
            href="/"
            className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={() => setMobileMenuOpen(false)}
          >
            Home
          </Link>
          <Link
            href="/dashboard"
            className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={() => setMobileMenuOpen(false)}
          >
            Dashboard
          </Link>
          <Link
            href="/admin"
            className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
            onClick={() => setMobileMenuOpen(false)}
          >
            Admin
          </Link>
        </div>
      )}
    </header>
  );
}
