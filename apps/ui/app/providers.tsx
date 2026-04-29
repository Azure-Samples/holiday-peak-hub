
'use client';

import { ReactNode } from 'react';
import { ChatWidget } from '@/components/organisms/ChatWidget';
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
            <ChatWidget />
          </PageSessionProvider>
        </ThemeProvider>
      </QueryProvider>
    </AuthProvider>
  );
}
