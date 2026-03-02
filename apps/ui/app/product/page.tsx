'use client';

import { useSearchParams } from 'next/navigation';
import { ProductPageClient } from './ProductPageClient';

export default function ProductPage() {
  const searchParams = useSearchParams();
  const id = searchParams.get('id') || '';

  return <ProductPageClient productId={id} />;
}
