'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/contexts/AuthContext';

export default function LogoutPage() {
  const router = useRouter();
  const { logout } = useAuth();

  useEffect(() => {
    let isMounted = true;

    const runLogout = async () => {
      try {
        await logout();
      } catch (error) {
        console.error('Logout flow failed:', error);
      } finally {
        if (isMounted) {
          router.replace('/auth/login');
          router.refresh();
        }
      }
    };

    void runLogout();

    return () => {
      isMounted = false;
    };
  }, [logout, router]);

  return (
    <div className="mx-auto w-full max-w-2xl px-6 py-16 text-center" role="status" aria-live="polite">
      Signing you out...
    </div>
  );
}