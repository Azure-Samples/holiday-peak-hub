'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

const TARGET_PATH = '/search?agentChat=1';

export default function ProductEnrichmentChatPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(TARGET_PATH);
  }, [router]);

  return (
    <main className="mx-auto flex min-h-[50vh] max-w-xl flex-col items-center justify-center gap-2 px-4 text-center">
      <p className="text-sm text-muted-foreground">Redirecting to search chat…</p>
      <Link className="text-sm font-medium underline" href={TARGET_PATH}>
        Continue to search chat
      </Link>
    </main>
  );
}
