
'use client';

import { ReactNode } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { QueryProvider } from '@/lib/providers/QueryProvider';
import { PageSessionProvider } from '@/lib/providers/PageSessionProvider';

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <QueryProvider>
        <ThemeProvider>
          <PageSessionProvider>
            {children}
          </PageSessionProvider>
        </ThemeProvider>
      </QueryProvider>
    </AuthProvider>
  );
}
