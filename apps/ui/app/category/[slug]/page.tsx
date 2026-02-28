import { CategoryPageClient } from '../CategoryPageClient';

export default async function CategorySlugPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <CategoryPageClient slug={slug || 'all'} />;
}
