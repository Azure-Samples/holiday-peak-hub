
'use client';

import { ReactNode } from 'react';
import dynamic from 'next/dynamic';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { QueryProvider } from '@/lib/providers/QueryProvider';
import { PageSessionProvider } from '@/lib/providers/PageSessionProvider';

const AuthProvider = dynamic(
  () => import('@/contexts/AuthContext').then((mod) => mod.AuthProvider),
  { ssr: false }
);

const ChatWidget = dynamic(
  () => import('@/components/organisms/ChatWidget').then((mod) => mod.ChatWidget),
  { ssr: false }
);

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
