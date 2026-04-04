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
      <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">{title}</h3>
      {resolvedProducts.length > 0 ? (
        <div className="flex flex-col gap-2 sm:flex-row sm:overflow-x-auto sm:pb-1" role="list" aria-label={`${title} mini product cards`}>
          {resolvedProducts.map((product) => (
            <Link
              key={`${title}-${product.sku}`}
              href={`/product?id=${encodeURIComponent(product.sku)}`}
              role="listitem"
              className="flex min-w-[200px] items-center gap-3 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-2 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm transition-all duration-200"
            >
              <div className="relative h-12 w-12 overflow-hidden rounded-lg bg-[var(--hp-surface-strong)]">
                <Image src={product.thumbnail} alt={product.title} fill className="object-cover" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-gray-900 dark:text-white">{product.title}</p>
                <p className="text-[11px] text-gray-400">${product.price.toFixed(2)}</p>
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
              className="whitespace-nowrap rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1 text-xs text-gray-600 dark:text-gray-300 hover:border-gray-400 dark:hover:border-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors duration-200"
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
