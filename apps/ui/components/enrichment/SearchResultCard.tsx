import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card } from '../molecules/Card';
import { PriceDisplay } from '../molecules/PriceDisplay';
import { UseCaseTags } from './UseCaseTags';
import { RelatedProductsRail } from './RelatedProductsRail';
import type { Product } from '../types';

export interface SearchResultCardProps {
  product: Product;
  relatedProductMap?: Record<string, Product>;
}

export const SearchResultCard: React.FC<SearchResultCardProps> = ({ product, relatedProductMap }) => {
  return (
    <Card className="overflow-hidden border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-[120px_1fr]">
        <Link
          href={`/product?id=${encodeURIComponent(product.sku)}`}
          className="relative aspect-square overflow-hidden rounded-xl bg-[var(--hp-surface-strong)]"
        >
          <Image
            src={product.thumbnail}
            alt={product.title}
            fill
            className="object-cover"
          />
        </Link>

        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <Link href={`/product?id=${encodeURIComponent(product.sku)}`} className="text-lg font-semibold text-[var(--hp-text)] hover:text-[var(--hp-primary)]">
                {product.title}
              </Link>
              <p className="text-sm text-[var(--hp-text-muted)]">{product.category}</p>
            </div>
            <PriceDisplay price={product.salePrice || product.price} msrp={product.msrp} currency={product.currency} size="md" />
          </div>

          <p className="mb-3 text-sm text-[var(--hp-text-muted)] line-clamp-3">
            {product.enrichedDescription || product.description}
          </p>

          <div className="space-y-3">
            <UseCaseTags useCases={product.useCases} />
            <RelatedProductsRail
              title="Complements"
              items={product.complementaryProducts}
              productMap={relatedProductMap}
            />
            <RelatedProductsRail
              title="Alternatives"
              items={product.substituteProducts}
              productMap={relatedProductMap}
            />
          </div>
        </div>
      </div>
    </Card>
  );
};

SearchResultCard.displayName = 'SearchResultCard';
