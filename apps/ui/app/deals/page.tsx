'use client';

import Link from 'next/link';
import { CommerceAgentLayout } from '@/components/templates/CommerceAgentLayout';
import { Card } from '@/components/molecules/Card';
import { ProductGrid } from '@/components/organisms/ProductGrid';
import { useProducts } from '@/lib/hooks/useProducts';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';

export default function DealsPage() {
  const { data: products = [], isLoading } = useProducts({ search: 'discount', limit: 8 });
  const items = mapApiProductsToUi(products);

  return (
    <CommerceAgentLayout
      sideCast={[
        {
          agentSlug: 'crm-campaign-intelligence',
          state: 'thinking',
          thinkingMessage: 'Showing campaigns most likely to convert your cohort.',
          position: 'bottom-right',
          size: 'sm',
          visible: true,
          className: 'hidden xl:block',
          mode: 'hint',
        },
      ]}
      telemetry="visible"
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-[var(--hp-text)]">Deals</h1>
          <p className="text-[var(--hp-text-muted)] mt-1">Campaign-selected offers likely to convert right now.</p>
        </div>

        <Card className="p-4 text-sm text-[var(--hp-text-muted)]">
          This route now keeps the campaign context visible instead of redirecting away immediately.
          <span className="ml-1">
            <Link href="/search?q=discount" className="text-[var(--hp-accent)] hover:underline">Open the full discounted search feed</Link>
          </span>
        </Card>

        <ProductGrid products={items} loading={isLoading} showSort={false} />
      </div>
    </CommerceAgentLayout>
  );
}
