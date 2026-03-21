import { MainLayout } from '@/components/templates/MainLayout';

export default function CategoryLoading() {
  return (
    <MainLayout>
      <div className="space-y-4" role="status" aria-live="polite">
        <div className="h-10 w-64 animate-pulse rounded bg-[var(--hp-surface-strong)]" />
        <div className="h-6 w-40 animate-pulse rounded bg-[var(--hp-surface-strong)]" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={`category-loading-${index}`}
              className="h-52 animate-pulse rounded-xl bg-[var(--hp-surface-strong)]"
            />
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
