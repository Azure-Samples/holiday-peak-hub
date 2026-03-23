'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { Input } from '@/components/atoms/Input';
import { getApiErrorMessage, getApiStatusCode } from '@/lib/api/errorPresentation';
import { useOrders } from '@/lib/hooks/useOrders';
import { useBrandShoppingFlow } from '@/lib/hooks/usePersonalization';
import { 
  FiPackage, FiHeart, FiMapPin, FiUser,
  FiShoppingBag, FiArrowRight
} from 'react-icons/fi';

const IDENTIFIER_PATTERN = /^[A-Za-z0-9._-]+$/;

export default function DashboardPage() {
  const { data: orders = [], isLoading: ordersLoading } = useOrders();
  const personalizationFlow = useBrandShoppingFlow();
  const {
    mutate: runPersonalization,
    data: personalizationData,
    error: personalizationError,
    isPending: personalizationPending,
    isError: personalizationIsError,
  } = personalizationFlow;

  const recentOrders = orders.slice(0, 3);
  const seedCustomerId = recentOrders[0]?.user_id ?? '';
  const seedSku = recentOrders[0]?.items?.[0]?.product_id ?? '';
  const [customerId, setCustomerId] = useState(seedCustomerId);
  const [sku, setSku] = useState(seedSku);
  const normalizedCustomerId = customerId.trim();
  const normalizedSku = sku.trim();
  const hasValidCustomerId = Boolean(normalizedCustomerId && IDENTIFIER_PATTERN.test(normalizedCustomerId));
  const hasValidSku = Boolean(normalizedSku && IDENTIFIER_PATTERN.test(normalizedSku));
  const canRefreshPersonalization = !personalizationPending && hasValidCustomerId && hasValidSku;

  const recommendationCount = personalizationData?.composed.recommendations.length ?? 0;
  const isPersonalizationEmpty = !personalizationPending
    && !personalizationIsError
    && recommendationCount === 0;
  const personalizationStatusMessage = personalizationPending
    ? 'Loading personalized recommendations.'
    : personalizationIsError
      ? getApiErrorMessage(personalizationError, 'Personalization could not be loaded.')
      : isPersonalizationEmpty
        ? 'No recommendations available for this customer and SKU.'
        : `Showing ${recommendationCount} personalized recommendation${recommendationCount === 1 ? '' : 's'}.`;

  useEffect(() => {
    if (!customerId && seedCustomerId) {
      setCustomerId(seedCustomerId);
    }
  }, [customerId, seedCustomerId]);

  useEffect(() => {
    if (!sku && seedSku) {
      setSku(seedSku);
    }
  }, [sku, seedSku]);

  useEffect(() => {
    if (!personalizationPending && !personalizationData && !personalizationError && hasValidCustomerId && hasValidSku) {
      runPersonalization({ customerId: normalizedCustomerId, sku: normalizedSku, quantity: 1, maxItems: 4 });
    }
  }, [
    hasValidCustomerId,
    hasValidSku,
    normalizedCustomerId,
    normalizedSku,
    personalizationData,
    personalizationError,
    personalizationPending,
    runPersonalization,
  ]);

  const stats = [
    { label: 'Total Orders', value: ordersLoading ? '…' : String(orders.length), icon: FiPackage, color: 'ocean' as const },
    { label: 'Wishlist Items', value: 'Unavailable', icon: FiHeart, color: 'lime' as const },
    { label: 'Saved Addresses', value: 'Unavailable', icon: FiMapPin, color: 'cyan' as const },
    { label: 'Rewards Points', value: 'Unavailable', icon: FiShoppingBag, color: 'ocean' as const },
  ];

  const getStatusBadge = (status: string) => {
    const configs: Record<string, { label: string; className: string }> = {
      delivered: { label: 'Delivered', className: 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300' },
      in_transit: { label: 'In Transit', className: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300' },
      processing: { label: 'Processing', className: 'bg-ocean-100 text-ocean-700 dark:bg-ocean-900 dark:text-ocean-300' },
    };
    const config = configs[status] ?? { label: status, className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            My Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Welcome back! Here&apos;s what&apos;s happening with your account.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => (
            <StatCard key={stat.label} {...stat} />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Recent Orders */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  Recent Orders
                </h2>
                <Link href="/orders">
                  <Button variant="outline" size="sm">
                    View All <FiArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </Link>
              </div>

              <div className="space-y-4">
                {ordersLoading && (
                  Array(3).fill(0).map((_, i) => (
                    <div key={i} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg animate-pulse h-20" />
                  ))
                )}
                {!ordersLoading && recentOrders.map((order) => (
                  <div
                    key={order.id}
                    className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <Link
                          href={`/order/${order.id}`}
                          className="font-semibold text-ocean-500 dark:text-ocean-300 hover:underline"
                        >
                          {order.id}
                        </Link>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {new Date(order.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      {getStatusBadge(order.status)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {order.items.length} item{order.items.length !== 1 ? 's' : ''}
                      </span>
                      <span className="font-bold text-gray-900 dark:text-white">
                        ${order.total.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
                {!ordersLoading && recentOrders.length === 0 && (
                  <p
                    className="text-sm text-gray-600 dark:text-gray-400"
                    role="status"
                    aria-live="polite"
                  >
                    No orders yet.
                  </p>
                )}
              </div>
            </Card>

            {/* Recommended Products */}
            <Card className="p-6">
              <div className="mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Recommended for You
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                  Live personalization flow using catalog, profile, pricing, ranking, and compose endpoints.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                <div>
                  <label htmlFor="dashboard-customer-id" className="sr-only">Customer ID</label>
                  <Input
                    id="dashboard-customer-id"
                    name="dashboard-customer-id"
                    value={customerId}
                    onChange={(event) => setCustomerId(event.target.value)}
                    placeholder="customer-100"
                    ariaLabel="Customer ID"
                    aria-describedby="dashboard-personalization-status"
                  />
                </div>
                <div>
                  <label htmlFor="dashboard-sku" className="sr-only">Product SKU</label>
                  <Input
                    id="dashboard-sku"
                    name="dashboard-sku"
                    value={sku}
                    onChange={(event) => setSku(event.target.value)}
                    placeholder="seed-product-0001"
                    ariaLabel="Product SKU"
                    aria-describedby="dashboard-personalization-status"
                  />
                </div>
              </div>

              <div className="mb-5 flex items-center gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => runPersonalization({ customerId: normalizedCustomerId, sku: normalizedSku, quantity: 1, maxItems: 4 })}
                  disabled={!canRefreshPersonalization}
                  aria-label="Refresh recommendations"
                  aria-describedby="dashboard-personalization-status"
                >
                  {personalizationPending ? 'Refreshing…' : 'Refresh Recommendations'}
                </Button>
                {personalizationData?.offers ? (
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Offer preview: ${personalizationData.offers.final_price.toFixed(2)} from ${personalizationData.offers.base_price.toFixed(2)}
                  </p>
                ) : null}
              </div>

              <p
                id="dashboard-personalization-status"
                className="sr-only"
                role="status"
                aria-live={personalizationIsError ? 'assertive' : 'polite'}
                aria-atomic="true"
              >
                {personalizationStatusMessage}
                {personalizationIsError && getApiStatusCode(personalizationError)
                  ? ` Backend status: ${getApiStatusCode(personalizationError)}.`
                  : ''}
              </p>

              {personalizationIsError ? (
                <div
                  className="mb-4 rounded-lg border border-red-300 p-3 text-red-700 dark:border-red-900 dark:text-red-300"
                  role="alert"
                  aria-live="assertive"
                >
                  <p>
                    {getApiErrorMessage(personalizationFlow.error, 'Personalization could not be loaded.')}
                  </p>
                  {getApiStatusCode(personalizationFlow.error) ? (
                    <p className="mt-1 text-xs">Backend status: {getApiStatusCode(personalizationFlow.error)}</p>
                  ) : null}
                </div>
              ) : null}

              {personalizationPending ? (
                <div className="grid grid-cols-2 gap-4">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <div key={index} className="aspect-square bg-gray-50 dark:bg-gray-800 rounded-lg animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {personalizationData?.composed.recommendations.map((item) => (
                    <RecommendedProduct
                      key={`${item.sku}-${item.score}`}
                      sku={item.sku}
                      title={item.title}
                      score={item.score}
                    />
                  ))}
                </div>
              )}

              {isPersonalizationEmpty ? (
                <p
                  className="text-sm text-gray-600 dark:text-gray-400"
                  role="status"
                  aria-live="polite"
                >
                  No recommendations available for this customer and SKU.
                </p>
              ) : null}
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Quick Actions
              </h3>
              <div className="space-y-3">
                <Link href="/orders">
                  <Button variant="outline" className="w-full justify-start">
                    <FiPackage className="mr-2" />
                    View All Orders
                  </Button>
                </Link>
                <Link href="/profile">
                  <Button variant="outline" className="w-full justify-start">
                    <FiUser className="mr-2" />
                    Edit Profile
                  </Button>
                </Link>
                <Link href="/wishlist">
                  <Button variant="outline" className="w-full justify-start">
                    <FiHeart className="mr-2" />
                    My Wishlist
                  </Button>
                </Link>
                <Link href="/categories">
                  <Button variant="outline" className="w-full justify-start">
                    <FiMapPin className="mr-2" />
                    Browse Categories
                  </Button>
                </Link>
              </div>
            </Card>

            {/* Rewards */}
            <Card className="p-6 bg-gradient-to-br from-ocean-50 to-cyan-50 dark:from-ocean-950 dark:to-cyan-950 border-ocean-200 dark:border-ocean-800">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-ocean-500 dark:bg-ocean-300 rounded-full flex items-center justify-center">
                  <FiShoppingBag className="w-6 h-6 text-white dark:text-gray-900" />
                </div>
                <div>
                  <h3
                    className="font-bold text-gray-900 dark:text-white"
                    aria-describedby="dashboard-rewards-unavailable"
                  >
                    Rewards Program
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Unavailable
                  </p>                </div>
              </div>
              <p
                id="dashboard-rewards-unavailable"
                className="text-sm text-gray-600 dark:text-gray-400 mb-4"
                role="note"
              >
                Rewards data is not available in the current API contract.
              </p>
              <Button variant="outline" size="sm" className="w-full border-ocean-500 text-ocean-500 dark:border-ocean-300 dark:text-ocean-300">
                Learn More
              </Button>
            </Card>

            {/* Support */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Need Help?
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Our customer support team is here to assist you 24/7
              </p>
              <Link href="/search?agentChat=1">
                <Button className="w-full bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900">
                  Contact Support
                </Button>
              </Link>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

function StatCard({ label, value, icon: Icon, color }: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'ocean' | 'lime' | 'cyan';
}) {
  const colorClasses = {
    ocean: 'bg-ocean-100 dark:bg-ocean-900 text-ocean-500 dark:text-ocean-300',
    lime: 'bg-lime-100 dark:bg-lime-900 text-lime-500 dark:text-lime-300',
    cyan: 'bg-cyan-100 dark:bg-cyan-900 text-cyan-500 dark:text-cyan-300',
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{label}</p>
          <p
            className="text-3xl font-bold text-gray-900 dark:text-white"
            aria-label={value === 'Unavailable'
              ? `${label} unavailable in the current API contract`
              : `${label}: ${value}`}
          >
            {value}
          </p>
        </div>
        <div className={`w-14 h-14 rounded-full flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-7 h-7" />
        </div>
      </div>
    </Card>
  );
}

function RecommendedProduct({ sku, title, score }: { sku: string; title: string; score: number }) {
  return (
    <Link href={`/product/${encodeURIComponent(sku)}`}>
      <div className="group cursor-pointer">
        <div className="aspect-square bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-lg mb-2 group-hover:scale-105 transition-transform" />
        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-1 line-clamp-2">
          {title}
        </h4>
        <p className="text-xs text-gray-600 dark:text-gray-400">{sku}</p>
        <p className="text-sm font-bold text-ocean-500 dark:text-ocean-300">Score: {score.toFixed(2)}</p>
      </div>
    </Link>
  );
}
