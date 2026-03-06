'use client';

import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Badge } from '@/components/atoms/Badge';
import { useCategories } from '@/lib/hooks/useCategories';
import { getApiErrorMessage, getApiStatusCode } from '@/lib/api/errorPresentation';

export default function CategoriesPage() {
  const { data: categories = [], isLoading, isError, error } = useCategories();
  const errorStatus = getApiStatusCode(error);
  const errorMessage = getApiErrorMessage(
    error,
    'Categories could not be loaded. Please verify the cloud API configuration and try again.',
  );

  return (
    <MainLayout>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Categories</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Browse all categories and open agent-enriched product collections.
          </p>
        </div>
        <Link
          href="/category?slug=all"
          className="text-ocean-500 dark:text-ocean-300 hover:underline font-medium"
        >
          View all products
        </Link>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <Card key={index} className="p-6 animate-pulse">
              <div className="h-6 w-2/3 bg-gray-200 dark:bg-gray-700 rounded mb-3" />
              <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded" />
            </Card>
          ))}
        </div>
      )}

      {!isLoading && isError && (
        <Card className="p-6 border border-red-200 dark:border-red-900">
          <p className="text-red-600 dark:text-red-400">{errorMessage}</p>
          {errorStatus ? (
            <p className="mt-2 text-xs text-red-500 dark:text-red-300">Backend status: {errorStatus}</p>
          ) : null}
        </Card>
      )}

      {!isLoading && !isError && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map((category) => (
            <Link key={category.id} href={`/category?slug=${encodeURIComponent(category.id)}`}>
              <Card className="h-full p-6 hover:shadow-lg transition-all border border-gray-200 dark:border-gray-700">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white line-clamp-2">
                    {category.name}
                  </h2>
                  <Badge className="bg-ocean-500 text-white">Agent-ready</Badge>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
                  {category.description || 'Browse products in this category.'}
                </p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </MainLayout>
  );
}
