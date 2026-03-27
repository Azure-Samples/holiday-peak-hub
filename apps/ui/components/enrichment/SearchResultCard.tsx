import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card } from '../molecules/Card';
import { Badge } from '../atoms/Badge';
import { PriceDisplay } from '../molecules/PriceDisplay';
import { UseCaseTags } from './UseCaseTags';
import { RelatedProductsRail } from './RelatedProductsRail';
import type { Product } from '../types';

export interface SearchResultCardProps {
  product: Product;
  relatedProductMap?: Record<string, Product>;
}

export const SearchResultCard: React.FC<SearchResultCardProps> = ({ product, relatedProductMap }) => {
  const productHref = `/product?id=${encodeURIComponent(product.sku)}`;
  const finalPrice = product.salePrice || product.price;
  const isOnSale = Boolean(product.msrp && finalPrice < product.msrp);

  return (
    <Card className="overflow-hidden border border-[var(--hp-border)] bg-[var(--hp-surface)] p-4 shadow-sm">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-[144px_1fr]">
        <Link
          href={productHref}
          className="relative aspect-square overflow-hidden rounded-2xl bg-[var(--hp-surface-strong)]"
        >
          <Image
            src={product.thumbnail}
            alt={product.title}
            fill
            className="object-cover transition-transform duration-500 hover:scale-105"
          />

          <div className="absolute left-2 top-2 z-10 flex flex-wrap gap-1">
            {isOnSale ? <Badge variant="error" size="sm">Sale</Badge> : null}
            {!product.inStock ? <Badge variant="secondary" size="sm">Out of Stock</Badge> : null}
          </div>
        </Link>

        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wide text-[var(--hp-text-muted)]">
                {product.brand}
              </p>
              <Link href={productHref} className="text-lg font-semibold text-[var(--hp-text)] hover:text-[var(--hp-primary)] focus-visible:rounded-sm">
                {product.title}
              </Link>
              <p className="text-sm text-[var(--hp-text-muted)]">{product.category}</p>

              {product.rating ? (
                <p className="mt-1 text-xs text-[var(--hp-text-muted)]">
                  {'★'.repeat(Math.max(1, Math.round(product.rating)))} {product.rating.toFixed(1)}
                  {product.reviewCount ? ` (${product.reviewCount})` : ''}
                </p>
              ) : null}
            </div>
            <PriceDisplay price={finalPrice} msrp={product.msrp} currency={product.currency} size="md" />
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
