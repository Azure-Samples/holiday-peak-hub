'use client';

import React, { useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { MainLayout } from '@/components/templates/MainLayout';
import { Badge } from '@/components/atoms/Badge';
import { Button } from '@/components/atoms/Button';
import { Card } from '@/components/molecules/Card';
import { useProduct } from '@/lib/hooks/useProducts';
import { mapApiProductToUiProduct } from '@/lib/utils/productMappers';
import { FiShoppingCart, FiTruck, FiShield, FiRotateCcw } from 'react-icons/fi';

export function ProductPageClient({ productId }: { productId: string }) {
  const { data: product, isLoading, isError } = useProduct(productId);

  const uiProduct = useMemo(() => (product ? mapApiProductToUiProduct(product) : null), [product]);

  return (
    <MainLayout>
      {isLoading && (
        <div className="animate-pulse space-y-6">
          <div className="h-6 w-1/3 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="aspect-square bg-gray-200 dark:bg-gray-700 rounded-2xl" />
            <div className="space-y-4">
              <div className="h-8 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-6 w-1/4 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-24 w-full bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
          </div>
        </div>
      )}

      {!isLoading && isError && (
        <Card className="p-6 border border-red-200 dark:border-red-900">
          <p className="text-red-600 dark:text-red-400">Product could not be loaded from the cloud backend.</p>
        </Card>
      )}

      {!isLoading && !isError && uiProduct && product && (
        <>
          <nav className="text-sm text-gray-600 dark:text-gray-400 mb-6 flex items-center gap-2">
            <Link href="/" className="hover:text-ocean-500 dark:hover:text-ocean-300">Home</Link>
            <span>/</span>
            <Link
              href={`/category?slug=${encodeURIComponent(product.category_id)}`}
              className="hover:text-ocean-500 dark:hover:text-ocean-300"
            >
              {product.category_id}
            </Link>
            <span>/</span>
            <span className="text-gray-900 dark:text-white">{product.name}</span>
          </nav>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 mb-12">
            <div className="aspect-square rounded-2xl overflow-hidden bg-gray-100 dark:bg-gray-800">
              <Image
                src={uiProduct.thumbnail || '/images/products/p1.jpg'}
                alt={product.name}
                width={800}
                height={800}
                className="w-full h-full object-cover"
              />
            </div>

            <div>
              <div className="flex items-center gap-3 mb-4">
                <Badge className="bg-ocean-500 text-white">Agent Enriched</Badge>
                {product.in_stock ? (
                  <Badge className="bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300">In Stock</Badge>
                ) : (
                  <Badge className="bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300">Out of Stock</Badge>
                )}
              </div>

              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">{product.name}</h1>
              <p className="text-gray-600 dark:text-gray-400 mb-6">{product.description}</p>

              <div className="flex items-end gap-3 mb-6">
                <span className="text-4xl font-bold text-ocean-500 dark:text-ocean-300">
                  ${product.price.toFixed(2)}
                </span>
                {typeof product.rating === 'number' && (
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    ★ {product.rating.toFixed(1)}{product.review_count ? ` (${product.review_count})` : ''}
                  </span>
                )}
              </div>

              <Button
                size="lg"
                className="w-full sm:w-auto bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900"
                disabled={!product.in_stock}
              >
                <FiShoppingCart className="mr-2 w-5 h-5" />
                Add to Cart
              </Button>

              <Link
                href={`/agents/product-enrichment-chat?sku=${encodeURIComponent(product.id)}`}
                className="inline-flex w-full sm:w-auto mt-3 sm:mt-0 sm:ml-3"
              >
                <Button variant="outline" size="lg" className="w-full">Ask Product Agent</Button>
              </Link>

              {uiProduct.tags && uiProduct.tags.length > 0 && (
                <div className="mt-6 flex flex-wrap gap-2">
                  {uiProduct.tags.map((tag) => (
                    <Badge key={tag} className="bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>

          <Card className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Feature icon={<FiTruck className="w-6 h-6" />} title="Fast Delivery" description="Delivery ETA from logistics agents." />
              <Feature icon={<FiRotateCcw className="w-6 h-6" />} title="Flexible Returns" description="Returns support assisted by agents." />
              <Feature icon={<FiShield className="w-6 h-6" />} title="Quality Insights" description="Product details enriched by specialist agents." />
            </div>
          </Card>
        </>
      )}
    </MainLayout>
  );
}

function Feature({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="text-center">
      <div className="text-ocean-500 dark:text-ocean-300 mb-2 flex justify-center">{icon}</div>
      <h4 className="font-semibold text-gray-900 dark:text-white text-sm mb-1">{title}</h4>
      <p className="text-xs text-gray-600 dark:text-gray-400">{description}</p>
    </div>
  );
}
