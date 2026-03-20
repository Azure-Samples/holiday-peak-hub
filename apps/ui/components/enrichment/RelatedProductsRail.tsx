import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import type { Product } from '../types';

export interface RelatedProductsRailProps {
  title: string;
  items?: string[];
  productMap?: Record<string, Product>;
}

export const RelatedProductsRail: React.FC<RelatedProductsRailProps> = ({
  title,
  items = [],
  productMap,
}) => {
  if (items.length === 0) {
    return null;
  }

  const resolvedProducts = items
    .map((item) => productMap?.[item])
    .filter((product): product is Product => Boolean(product));

  return (
    <section aria-label={title}>
      <h3 className="mb-2 text-sm font-semibold text-[var(--hp-text)]">{title}</h3>
      {resolvedProducts.length > 0 ? (
        <div className="flex flex-col gap-2 sm:flex-row sm:overflow-x-auto sm:pb-1" role="list" aria-label={`${title} mini product cards`}>
          {resolvedProducts.map((product) => (
            <Link
              key={`${title}-${product.sku}`}
              href={`/product?id=${encodeURIComponent(product.sku)}`}
              role="listitem"
              className="flex min-w-[220px] items-center gap-3 rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] p-2 hover:border-[var(--hp-primary)]"
            >
              <div className="relative h-12 w-12 overflow-hidden rounded-lg bg-[var(--hp-surface-strong)]">
                <Image src={product.thumbnail} alt={product.title} fill className="object-cover" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-[var(--hp-text)]">{product.title}</p>
                <p className="text-xs text-[var(--hp-text-muted)]">${product.price.toFixed(2)}</p>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="flex gap-2 overflow-x-auto pb-1" role="list">
          {items.map((item) => (
            <Link
              key={`${title}-${item}`}
              href={`/search?q=${encodeURIComponent(item)}`}
              role="listitem"
              className="whitespace-nowrap rounded-full border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-1 text-sm text-[var(--hp-text)] hover:border-[var(--hp-primary)]"
            >
              {item}
            </Link>
          ))}
        </div>
      )}
    </section>
  );
};

RelatedProductsRail.displayName = 'RelatedProductsRail';
