import { ProductPageClient } from './ProductPageClient';

type ProductPageProps = {
  searchParams?: Promise<{ id?: string }>;
};

export default async function ProductPage({ searchParams }: ProductPageProps) {
  const resolvedSearchParams = (await searchParams) ?? {};
  const id = resolvedSearchParams.id || '';

  return <ProductPageClient productId={id} />;
}
