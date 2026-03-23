'use client';

import { useEffect, useMemo, useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Badge } from '@/components/atoms/Badge';
import { Select } from '@/components/atoms/Select';
import { Button } from '@/components/atoms/Button';
import {
  useAdminServiceDashboard,
  DEFAULT_ADMIN_SERVICE_RANGE,
  ADMIN_SERVICE_RANGE_OPTIONS,
} from '@/lib/hooks/useAdminServiceDashboard';
import { useProducts, useTriggerProductEnrichment } from '@/lib/hooks/useProducts';
import type { AdminServiceDomain, AgentMonitorTimeRange, AdminServiceStatus, AgentTraceStatus } from '@/lib/types/api';

const STATUS_BADGE_VARIANT: Record<AdminServiceStatus, 'success' | 'warning' | 'danger' | 'secondary'> = {
  healthy: 'success',
  warning: 'warning',
  error: 'danger',
  unknown: 'secondary',
};

const ACTIVITY_STATUS_BADGE_VARIANT: Record<AgentTraceStatus, 'success' | 'warning' | 'danger' | 'secondary'> = {
  ok: 'success',
  warning: 'warning',
  error: 'danger',
  unknown: 'secondary',
};

function toTitleCase(value: string): string {
  return value
    .split(/[-_\s]+/)
    .filter((part) => part.length > 0)
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(' ');
}

export interface AdminServiceDashboardPageProps {
  domain: AdminServiceDomain;
  service: string;
}

export function AdminServiceDashboardPage({ domain, service }: AdminServiceDashboardPageProps) {
  const [timeRange, setTimeRange] = useState<AgentMonitorTimeRange>(DEFAULT_ADMIN_SERVICE_RANGE);
  const [triggerProductId, setTriggerProductId] = useState('');
  const [triggerStatusMessage, setTriggerStatusMessage] = useState<string | null>(null);
  const [triggerErrorMessage, setTriggerErrorMessage] = useState<string | null>(null);
  const { data, isLoading, isError, isFetching, error, refetch } = useAdminServiceDashboard(domain, service, timeRange);
  const {
    data: products = [],
    isLoading: isProductsLoading,
    isError: isProductsError,
  } = useProducts({ limit: 100 });
  const triggerEnrichment = useTriggerProductEnrichment();

  const showProductTriggerCard = domain === 'ecommerce' && service === 'products';
  const productOptions = useMemo(
    () =>
      products.map((product) => ({
        value: product.id,
        label: `${product.id} — ${product.name}`,
      })),
    [products],
  );

  useEffect(() => {
    if (!showProductTriggerCard) {
      return;
    }

    if (triggerProductId || productOptions.length === 0) {
      return;
    }

    setTriggerProductId(String(productOptions[0].value));
  }, [showProductTriggerCard, triggerProductId, productOptions]);

  const handleTriggerEnrichment = async () => {
    const normalizedProductId = triggerProductId.trim();
    if (!normalizedProductId) {
      setTriggerErrorMessage('Select a product to trigger enrichment.');
      setTriggerStatusMessage(null);
      return;
    }

    setTriggerErrorMessage(null);
    setTriggerStatusMessage(null);

    try {
      const response = await triggerEnrichment.mutateAsync({
        productId: normalizedProductId,
        payload: {
          trigger_source: 'admin_ecommerce_products',
        },
      });

      const queuedAt = new Date(response.queued_at).toLocaleString();
      setTriggerStatusMessage(`Queued at ${queuedAt}`);
      await refetch();
    } catch (triggerError: unknown) {
      const message =
        triggerError instanceof Error ? triggerError.message : 'Failed to trigger enrichment.';
      setTriggerErrorMessage(message);
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{toTitleCase(service)} Service</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-400">
              Domain <span className="font-semibold">{domain}</span> · Service <span className="font-semibold">{service}</span>
            </p>
            {data && (
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Agent {data.agent_service} · Updated {new Date(data.generated_at).toLocaleString()}
              </p>
            )}
          </div>
          <Badge variant={data?.tracing_enabled ? 'success' : 'warning'}>
            {data?.tracing_enabled ? 'Tracing enabled' : 'Tracing unavailable'}
          </Badge>
        </header>

        <section className="flex flex-wrap items-center gap-3">
          <label htmlFor="admin-service-range" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Time range
          </label>
          <div className="w-52">
            <Select
              name="admin-service-range"
              ariaLabel="Admin service time range"
              value={timeRange}
              options={ADMIN_SERVICE_RANGE_OPTIONS}
              onChange={(event) => setTimeRange(event.target.value as AgentMonitorTimeRange)}
            />
          </div>
          <Button
            variant="secondary"
            onClick={() => {
              void refetch();
            }}
            loading={isFetching}
            ariaLabel="Refresh service dashboard"
          >
            Refresh
          </Button>
        </section>

        {showProductTriggerCard && (
          <Card className="p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="w-full sm:max-w-sm">
                <label
                  htmlFor="trigger-product-id"
                  className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Product ID
                </label>
                <Select
                  name="trigger-product-id"
                  value={triggerProductId}
                  onChange={(event) => setTriggerProductId(event.target.value)}
                  options={productOptions}
                  placeholder={isProductsLoading ? 'Loading products...' : 'Select a product'}
                  disabled={isProductsLoading || productOptions.length === 0}
                  ariaLabel="Product ID"
                />
              </div>
              <Button
                onClick={() => {
                  void handleTriggerEnrichment();
                }}
                loading={triggerEnrichment.isPending}
                disabled={isProductsLoading || productOptions.length === 0 || !triggerProductId}
                ariaLabel="Trigger enrichment"
              >
                Trigger enrichment
              </Button>
            </div>
            {isProductsError && (
              <p className="mt-2 text-sm text-red-700 dark:text-red-400">
                Unable to load products from CRUD service.
              </p>
            )}
            {!isProductsLoading && !isProductsError && productOptions.length === 0 && (
              <p className="mt-2 text-sm text-yellow-700 dark:text-yellow-400">
                No products available in CRUD service.
              </p>
            )}
            {triggerStatusMessage && (
              <p className="mt-2 text-sm text-green-700 dark:text-green-400">{triggerStatusMessage}</p>
            )}
            {triggerErrorMessage && (
              <p className="mt-2 text-sm text-red-700 dark:text-red-400">{triggerErrorMessage}</p>
            )}
          </Card>
        )}

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading service dashboard…</Card>}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Failed to load service dashboard data: {error instanceof Error ? error.message : 'Unknown error'}
          </Card>
        )}

        {data && (
          <>
            <section aria-label="Status cards" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {data.status_cards.length === 0 ? (
                <Card className="p-4 sm:col-span-2 lg:col-span-4">
                  <p className="text-sm text-gray-500 dark:text-gray-400">No status metrics available for this service yet.</p>
                </Card>
              ) : (
                data.status_cards.map((card) => (
                  <Card key={card.label} className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{card.label}</p>
                      <Badge variant={STATUS_BADGE_VARIANT[card.status]}>{card.status}</Badge>
                    </div>
                    <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">{card.value}</p>
                  </Card>
                ))
              )}
            </section>

            <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="p-0 overflow-hidden">
                <div className="border-b border-gray-200 p-4 dark:border-gray-700">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Activity</h2>
                </div>

                {data.activity.length === 0 ? (
                  <p className="p-4 text-sm text-gray-500 dark:text-gray-400">No activity rows for this time range.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-900/40">
                        <tr>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Timestamp</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Event</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Entity</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Status</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Latency</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.activity.map((row) => (
                          <tr key={row.id} className="border-t border-gray-200 dark:border-gray-700">
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{new Date(row.timestamp).toLocaleString()}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.event}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.entity}</td>
                            <td className="px-4 py-2">
                              <Badge variant={ACTIVITY_STATUS_BADGE_VARIANT[row.status]}>{row.status}</Badge>
                            </td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{Math.round(row.latency_ms)} ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>

              <Card className="p-0 overflow-hidden">
                <div className="border-b border-gray-200 p-4 dark:border-gray-700">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Model usage</h2>
                </div>

                {data.model_usage.length === 0 ? (
                  <p className="p-4 text-sm text-gray-500 dark:text-gray-400">No model usage available.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-900/40">
                        <tr>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Model</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Tier</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Requests</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Tokens</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Avg latency</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.model_usage.map((row) => (
                          <tr key={`${row.model_tier}-${row.model_name}`} className="border-t border-gray-200 dark:border-gray-700">
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.model_name}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.model_tier}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.requests.toLocaleString()}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.total_tokens.toLocaleString()}</td>
                            <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{Math.round(row.avg_latency_ms)} ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </section>
          </>
        )}
      </div>
    </MainLayout>
  );
}

export default AdminServiceDashboardPage;
