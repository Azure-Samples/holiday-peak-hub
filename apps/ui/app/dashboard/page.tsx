'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { CommerceAgentLayout } from '@/components/templates/CommerceAgentLayout';
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
      delivered: { label: 'Delivered', className: 'bg-[var(--hp-accent-soft)] text-[var(--hp-accent)]' },
      in_transit: { label: 'In Transit', className: 'bg-[color:color-mix(in_srgb,var(--hp-focus)_18%,transparent)] text-[var(--hp-focus)]' },
      processing: { label: 'Processing', className: 'bg-[var(--hp-primary-soft)] text-[var(--hp-primary)]' },
    };
    const config = configs[status] ?? { label: status, className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  return (
    <CommerceAgentLayout
      sideCast={[
        {
          agentSlug: 'inventory-health-check',
          state: 'thinking',
          thinkingMessage: 'All of your saved-for-later items are in stock.',
          position: 'bottom-left',
          size: 'sm',
          visible: true,
          className: 'hidden xl:block',
          mode: 'hint',
        },
      ]}
      telemetry="visible"
    >
      <div className="max-w-7xl mx-auto px-4 md:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
            Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Welcome back. Here&apos;s what&apos;s happening with your account.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
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
                <Link
                  href="/orders"
                  className="inline-flex items-center justify-center rounded-xl border border-[var(--hp-border)] px-3 py-1.5 text-xs font-semibold text-[var(--hp-text)] transition-colors hover:bg-[var(--hp-surface-strong)]"
                >
                  View All <FiArrowRight className="ml-2 w-4 h-4" />
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
                          className="font-semibold text-[var(--hp-primary)] hover:text-[var(--hp-primary-hover)] hover:underline"
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
                <DashboardActionLink href="/orders" icon={<FiPackage className="mr-2" />}>View All Orders</DashboardActionLink>
                <DashboardActionLink href="/profile" icon={<FiUser className="mr-2" />}>Edit Profile</DashboardActionLink>
                <DashboardActionLink href="/wishlist" icon={<FiHeart className="mr-2" />}>My Wishlist</DashboardActionLink>
                <DashboardActionLink href="/categories" icon={<FiMapPin className="mr-2" />}>Browse Categories</DashboardActionLink>
              </div>
            </Card>

            {/* Rewards */}
            <Card className="p-6 border-[var(--hp-border)] bg-[var(--hp-surface-strong)]">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-[var(--hp-primary)] rounded-full flex items-center justify-center">
                  <FiShoppingBag className="w-6 h-6 text-white" />
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
              <Button variant="outline" size="sm" className="w-full border-[var(--hp-primary)] text-[var(--hp-primary)] hover:bg-[var(--hp-primary-soft)]">
                Learn More
              </Button>
            </Card>

            {/* Support */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Need Help?
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Open the product search assistant to compare live retrieval results.
              </p>
              <Link
                href="/search?agentChat=1"
                className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--hp-primary)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--hp-primary-hover)]"
              >
                Open Product Agent
              </Link>
            </Card>
          </div>
        </div>
      </div>
    </CommerceAgentLayout>
  );
}

function DashboardActionLink({ href, icon, children }: { href: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex w-full items-center justify-start rounded-xl border border-[var(--hp-border)] px-4 py-2 text-sm font-semibold text-[var(--hp-text)] transition-colors hover:bg-[var(--hp-surface-strong)]"
    >
      {icon}
      {children}
    </Link>
  );
}

function StatCard({ label, value, icon: Icon, color: _color }: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'ocean' | 'lime' | 'cyan';
}) {
  return (
    <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 shadow-sm">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center">
          <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
        </div>
      </div>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-1">{label}</p>
      <p
        className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums"
        aria-label={value === 'Unavailable'
          ? `${label} unavailable in the current API contract`
          : `${label}: ${value}`}
      >
        {value}
      </p>
    </div>
  );
}

function RecommendedProduct({ sku, title, score }: { sku: string; title: string; score: number }) {
  return (
    <Link href={`/product/${encodeURIComponent(sku)}`}>
      <div className="group cursor-pointer">
        <div className="aspect-square bg-gray-50 dark:bg-gray-800 rounded-xl mb-2 group-hover:shadow-md transition-shadow duration-200 border border-gray-100 dark:border-gray-800" />
        <h4 className="text-xs font-medium text-gray-900 dark:text-white mb-0.5 line-clamp-2">
          {title}
        </h4>
        <p className="text-[11px] text-gray-400">{sku}</p>
        <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mt-1">Score: {score.toFixed(2)}</p>
      </div>
    </Link>
  );
}
