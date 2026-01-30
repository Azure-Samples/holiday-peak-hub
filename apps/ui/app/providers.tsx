
'use client';

import { ReactNode } from 'react';
import dynamic from 'next/dynamic';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { QueryProvider } from '@/lib/providers/QueryProvider';

const AuthProvider = dynamic(
  () => import('@/contexts/AuthContext').then((mod) => mod.AuthProvider),
  { ssr: false }
);

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <QueryProvider>
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </QueryProvider>
    </AuthProvider>
  );
}
