import { useMemo } from 'react';
import type { Product } from '@/components/types';

export interface ProductSimilarityEdge {
  source: string;
  target: string;
  strength: number;
  reason: 'category' | 'brand' | 'tags';
}

const MIN_EDGE_STRENGTH = 0.45;
const MAX_EDGES = 36;

function normalizeText(value: unknown): string {
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
}

function normalizeTags(product: Product): string[] {
  return (Array.isArray(product.tags) ? product.tags : [])
    .map((tag) => normalizeText(tag))
    .filter((tag) => tag.length > 0);
}

function scorePair(left: Product, right: Product): ProductSimilarityEdge | null {
  let strength = 0;
  let reason: ProductSimilarityEdge['reason'] = 'category';

  const leftCategory = normalizeText(left.category);
  const rightCategory = normalizeText(right.category);
  const leftBrand = normalizeText(left.brand);
  const rightBrand = normalizeText(right.brand);

  if (leftCategory && leftCategory === rightCategory) {
    strength += 0.55;
    reason = 'category';
  }

  if (leftBrand && leftBrand === rightBrand) {
    strength += 0.2;
    reason = strength >= 0.55 ? reason : 'brand';
  }

  const leftTags = normalizeTags(left);
  const rightTags = new Set(normalizeTags(right));
  const overlapCount = leftTags.filter((tag) => rightTags.has(tag)).length;
  if (overlapCount > 0) {
    strength += Math.min(0.25, overlapCount * 0.08);
    reason = overlapCount >= 2 ? 'tags' : reason;
  }

  if (strength < MIN_EDGE_STRENGTH) {
    return null;
  }

  return {
    source: left.sku,
    target: right.sku,
    strength: Number(strength.toFixed(2)),
    reason,
  };
}

// No GoF pattern applies — deterministic data derivation over the current product slice.
export function useProductSimilarity(products: Product[]) {
  const similarities = useMemo(() => {
    const edges: ProductSimilarityEdge[] = [];

    for (let leftIndex = 0; leftIndex < products.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < products.length; rightIndex += 1) {
        const edge = scorePair(products[leftIndex], products[rightIndex]);
        if (edge) {
          edges.push(edge);
        }
      }
    }

    return edges
      .sort((left, right) => right.strength - left.strength)
      .slice(0, MAX_EDGES);
  }, [products]);

  return { similarities };
}
