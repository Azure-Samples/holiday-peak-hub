import { CategoryPageClient } from './CategoryPageClient';

type CategoryPageProps = {
  searchParams?: Promise<{ slug?: string }>;
};

export default async function CategoryPage({ searchParams }: CategoryPageProps) {
  const resolvedSearchParams = (await searchParams) ?? {};
  const slug = resolvedSearchParams.slug || 'all';

  return <CategoryPageClient slug={slug} />;
}
