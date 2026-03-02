'use client';

import { useSearchParams } from 'next/navigation';
import { CategoryPageClient } from './CategoryPageClient';

export default function CategoryPage() {
  const searchParams = useSearchParams();
  const slug = searchParams.get('slug') || 'all';

  return <CategoryPageClient slug={slug} />;
}
