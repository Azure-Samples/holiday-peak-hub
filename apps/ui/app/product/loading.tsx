import { MainLayout } from '@/components/templates/MainLayout';

export default function ProductLoading() {
  return (
    <MainLayout>
      <div className="space-y-6" role="status" aria-live="polite">
        <div className="h-8 w-48 animate-pulse rounded bg-[var(--hp-surface-strong)]" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="h-96 animate-pulse rounded-2xl bg-[var(--hp-surface-strong)]" />
          <div className="space-y-4">
            <div className="h-10 w-3/4 animate-pulse rounded bg-[var(--hp-surface-strong)]" />
            <div className="h-6 w-full animate-pulse rounded bg-[var(--hp-surface-strong)]" />
            <div className="h-6 w-2/3 animate-pulse rounded bg-[var(--hp-surface-strong)]" />
            <div className="h-12 w-40 animate-pulse rounded bg-[var(--hp-surface-strong)]" />
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
