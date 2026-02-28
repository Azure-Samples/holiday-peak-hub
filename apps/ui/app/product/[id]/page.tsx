import { ProductPageClient } from '../ProductPageClient';

export default async function ProductByIdPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProductPageClient productId={id || ''} />;
}
