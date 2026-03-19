import React from 'react';
import Link from 'next/link';

export interface RelatedProductsRailProps {
  title: string;
  items?: string[];
}

export const RelatedProductsRail: React.FC<RelatedProductsRailProps> = ({ title, items = [] }) => {
  if (items.length === 0) {
    return null;
  }

  return (
    <section aria-label={title}>
      <h3 className="mb-2 text-sm font-semibold text-[var(--hp-text)]">{title}</h3>
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
    </section>
  );
};

RelatedProductsRail.displayName = 'RelatedProductsRail';
