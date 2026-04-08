'use client';

import Link from 'next/link';
import { useMemo, type ComponentType } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Badge } from '@/components/atoms/Badge';
import { isTracingUnavailableError, useAgentMonitorDashboard } from '@/lib/hooks/useAgentMonitor';
import type { AgentHealthCardMetric, AgentHealthStatus, AgentMonitorTimeRange } from '@/lib/types/api';
import { 
  FiShoppingCart, FiPackage, FiTruck, FiUsers, FiTrendingUp,
  FiDatabase, FiLayers, FiSettings, FiShield, FiBarChart2,
  FiActivity, FiCpu, FiServer, FiTool, FiGlobe,
  FiBox, FiTag, FiGrid, FiCheckSquare, FiFileText, FiClock,
  FiMapPin
} from 'react-icons/fi';

const HOMEPAGE_SUMMARY_RANGE: AgentMonitorTimeRange = '24h';
const MINUTES_PER_DAY = 60 * 24;

const wholeNumberFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0,
});

const percentFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const errorRateFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

type HealthStatusCounts = Record<AgentHealthStatus, number>;

interface AdminHomepageSummary {
  activeServices: number;
  apiCalls24h: number;
  uptimePct: number;
  avgLatencyMs: number;
  avgErrorRatePct: number;
  totalThroughputRpm: number;
  statusCounts: HealthStatusCounts;
}

interface SystemHealthMetricViewModel {
  label: string;
  value: string;
  status: 'healthy' | 'warning' | 'critical';
}

const EMPTY_STATUS_COUNTS: HealthStatusCounts = {
  healthy: 0,
  degraded: 0,
  down: 0,
  unknown: 0,
};

function average(values: readonly number[]): number {
  if (values.length === 0) {
    return 0;
  }

  return values.reduce((total, value) => total + value, 0) / values.length;
}

function countByHealthStatus(cards: readonly AgentHealthCardMetric[]): HealthStatusCounts {
  const counts: HealthStatusCounts = { ...EMPTY_STATUS_COUNTS };

  for (const card of cards) {
    counts[card.status] += 1;
  }

  return counts;
}

// No GoF pattern applies: this is a straightforward data aggregation over monitor payload fields.
function aggregateHomepageSummary(cards: readonly AgentHealthCardMetric[]): AdminHomepageSummary {
  const statusCounts = countByHealthStatus(cards);
  const totalThroughputRpm = cards.reduce((total, card) => total + card.throughput_rpm, 0);

  const activeServices = cards.length;
  const apiCalls24h = Math.round(totalThroughputRpm * MINUTES_PER_DAY);
  const avgLatencyMs = average(cards.map((card) => card.latency_ms));
  const avgErrorRatePct = average(cards.map((card) => card.error_rate));
  const uptimePct =
    activeServices === 0
      ? 0
      : ((statusCounts.healthy + statusCounts.degraded) / activeServices) * 100;

  return {
    activeServices,
    apiCalls24h,
    uptimePct,
    avgLatencyMs,
    avgErrorRatePct,
    totalThroughputRpm,
    statusCounts,
  };
}

function formatWholeNumber(value: number): string {
  return wholeNumberFormatter.format(Math.round(value));
}

function formatPercent(value: number): string {
  return `${percentFormatter.format(value)}%`;
}

function formatErrorRate(value: number): string {
  return `${errorRateFormatter.format(value)}%`;
}

function statusFromErrorRate(errorRate: number): 'healthy' | 'warning' | 'critical' {
  if (errorRate >= 5) {
    return 'critical';
  }

  if (errorRate >= 1) {
    return 'warning';
  }

  return 'healthy';
}

export default function AdminPortalPage() {
  const { data, isLoading, isError, error, isFetching } = useAgentMonitorDashboard(HOMEPAGE_SUMMARY_RANGE);

  const isTracingUnavailable = Boolean(
    (data && !data.tracing_enabled) || (isError && isTracingUnavailableError(error))
  );

  const summary = useMemo(() => {
    if (!data || !data.tracing_enabled) {
      return null;
    }

    return aggregateHomepageSummary(data.health_cards);
  }, [data]);

  const hasSummaryData = Boolean(summary && data?.tracing_enabled && data.health_cards.length > 0);

  const getKpiValue = (valueBuilder: (liveSummary: AdminHomepageSummary) => string): string => {
    if (isLoading) {
      return 'Loading...';
    }

    if (!hasSummaryData || !summary) {
      return 'Unavailable';
    }

    return valueBuilder(summary);
  };

  const serviceCategories = [
    {
      name: 'CRM Services',
      description: 'Customer relationship management and personalization',
      services: [
        { name: 'Campaign Intelligence', icon: FiTrendingUp, url: '/admin/crm/campaigns' },
        { name: 'Profile Aggregation', icon: FiUsers, url: '/admin/crm/profiles' },
        { name: 'Segmentation', icon: FiGrid, url: '/admin/crm/segmentation' },
        { name: 'Support Assistance', icon: FiShield, url: '/admin/crm/support' },
      ],
    },
    {
      name: 'E-Commerce Services',
      description: 'Product catalog, cart, and order management',
      services: [
        { name: 'Catalog Search', icon: FiShoppingCart, url: '/admin/ecommerce/catalog' },
        { name: 'Cart Intelligence', icon: FiShoppingCart, url: '/admin/ecommerce/cart' },
        { name: 'Checkout Support', icon: FiCheckSquare, url: '/admin/ecommerce/checkout' },
        { name: 'Order Status', icon: FiPackage, url: '/admin/ecommerce/orders' },
        { name: 'Product Enrichment', icon: FiTag, url: '/admin/ecommerce/products' },
        { name: 'Truth Analytics', icon: FiBarChart2, url: '/admin/truth-analytics' },
        { name: 'Enrichment Monitor', icon: FiBarChart2, url: '/admin/enrichment-monitor' },
        { name: 'Agent Activity', icon: FiActivity, url: '/admin/agent-activity' },
      ],
    },
    {
      name: 'Inventory Services',
      description: 'Stock management and optimization',
      services: [
        { name: 'Health Check', icon: FiActivity, url: '/admin/inventory/health' },
        { name: 'Alerts & Triggers', icon: FiActivity, url: '/admin/inventory/alerts' },
        { name: 'JIT Replenishment', icon: FiBox, url: '/admin/inventory/replenishment' },
        { name: 'Reservation Validation', icon: FiCheckSquare, url: '/admin/inventory/reservation' },
      ],
    },
    {
      name: 'Logistics Services',
      description: 'Shipping and delivery optimization',
      services: [
        { name: 'Carrier Selection', icon: FiTruck, url: '/admin/logistics/carriers' },
        { name: 'ETA Computation', icon: FiClock, url: '/admin/logistics/eta' },
        { name: 'Returns Support', icon: FiPackage, url: '/admin/logistics/returns' },
        { name: 'Route Issue Detection', icon: FiMapPin, url: '/admin/logistics/routes' },
      ],
    },
    {
      name: 'Product Management',
      description: 'Product data and catalog management',
      services: [
        { name: 'ACP Transformation', icon: FiFileText, url: '/admin/products/acp' },
        { name: 'Assortment Optimization', icon: FiGrid, url: '/admin/products/assortment' },
        { name: 'Consistency Validation', icon: FiCheckSquare, url: '/admin/products/validation' },
        { name: 'Normalization', icon: FiLayers, url: '/admin/products/normalization' },
      ],
    },
  ];

  const systemStats = [
    {
      label: 'Active Services',
      value: getKpiValue((liveSummary) => formatWholeNumber(liveSummary.activeServices)),
      icon: FiServer,
    },
    {
      label: 'API Calls (24h)',
      value: getKpiValue((liveSummary) => formatWholeNumber(liveSummary.apiCalls24h)),
      icon: FiActivity,
    },
    {
      label: 'Uptime',
      value: getKpiValue((liveSummary) => formatPercent(liveSummary.uptimePct)),
      icon: FiCheckSquare,
    },
    {
      label: 'Avg Response',
      value: getKpiValue((liveSummary) => `${formatWholeNumber(liveSummary.avgLatencyMs)}ms`),
      icon: FiCpu,
    },
  ];

  const systemHealthMetrics = useMemo<SystemHealthMetricViewModel[]>(() => {
    if (isLoading) {
      return [
        { label: 'Healthy Services', value: 'Loading...', status: 'warning' as const },
        { label: 'Degraded Services', value: 'Loading...', status: 'warning' as const },
        { label: 'Down Services', value: 'Loading...', status: 'warning' as const },
        { label: 'Avg Error Rate', value: 'Loading...', status: 'warning' as const },
        { label: 'Total Throughput/min', value: 'Loading...', status: 'warning' as const },
        { label: 'Trace Events', value: 'Loading...', status: 'warning' as const },
      ];
    }

    if (!hasSummaryData || !summary || !data) {
      return [
        { label: 'Healthy Services', value: 'Unavailable', status: 'critical' as const },
        { label: 'Degraded Services', value: 'Unavailable', status: 'critical' as const },
        { label: 'Down Services', value: 'Unavailable', status: 'critical' as const },
        { label: 'Avg Error Rate', value: 'Unavailable', status: 'critical' as const },
        { label: 'Total Throughput/min', value: 'Unavailable', status: 'critical' as const },
        { label: 'Trace Events', value: 'Unavailable', status: 'critical' as const },
      ];
    }

    return [
      {
        label: 'Healthy Services',
        value: formatWholeNumber(summary.statusCounts.healthy),
        status: summary.statusCounts.down > 0 || summary.statusCounts.degraded > 0 ? 'warning' : 'healthy',
      },
      {
        label: 'Degraded Services',
        value: formatWholeNumber(summary.statusCounts.degraded),
        status: summary.statusCounts.degraded > 0 ? 'warning' : 'healthy',
      },
      {
        label: 'Down Services',
        value: formatWholeNumber(summary.statusCounts.down),
        status: summary.statusCounts.down > 0 ? 'critical' : 'healthy',
      },
      {
        label: 'Avg Error Rate',
        value: formatErrorRate(summary.avgErrorRatePct),
        status: statusFromErrorRate(summary.avgErrorRatePct),
      },
      {
        label: 'Total Throughput/min',
        value: `${formatWholeNumber(summary.totalThroughputRpm)} rpm`,
        status: summary.totalThroughputRpm > 0 ? 'healthy' : 'warning',
      },
      {
        label: 'Trace Events',
        value: formatWholeNumber(data.trace_feed.length),
        status: data.trace_feed.length > 0 ? 'healthy' : 'warning',
      },
    ];
  }, [data, hasSummaryData, isLoading, summary]);

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 md:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
            Admin Portal
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Central hub for managing all backend services and system operations
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-2" aria-live="polite">
            Homepage KPIs reflect live monitor data for the last 24 hours.
            {isFetching && !isLoading ? ' Refreshing…' : ''}
          </p>
          {isTracingUnavailable && (
            <p className="text-xs text-amber-600 dark:text-amber-400 mt-1" aria-live="polite">
              Monitoring data is currently unavailable because tracing is disabled or unreachable.
            </p>
          )}
        </div>

        {/* System Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {systemStats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 shadow-sm">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center">
                    <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                  </div>
                </div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-1">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">{stat.value}</p>
              </div>
            );
          })}
        </div>

        {/* Quick Actions */}
        <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 shadow-sm mb-8">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            Quick Actions
          </h2>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
            <QuickActionButton icon={FiBarChart2} label="Analytics" />
            <QuickActionButton icon={FiSettings} label="Settings" />
            <QuickActionButton icon={FiDatabase} label="Database" />
            <QuickActionButton icon={FiShield} label="Security" />
            <QuickActionButton icon={FiTool} label="Tools" />
            <QuickActionButton icon={FiGlobe} label="API Docs" />
          </div>
        </div>

        {/* Service Categories */}
        <div className="space-y-8">
          {serviceCategories.map((category) => (
            <div key={category.name}>
              <div className="mb-3">
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                  {category.name}
                </h2>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {category.description}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {category.services.map((service) => {
                  const Icon = service.icon;
                  return (
                    <Link key={service.name} href={service.url}>
                      <div className="group rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 hover:shadow-md hover:border-gray-200 dark:hover:border-gray-700 transition-all duration-200 cursor-pointer">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="w-9 h-9 rounded-lg bg-gray-50 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 group-hover:bg-gray-100 dark:group-hover:bg-gray-700 transition-colors">
                            <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                          </div>
                          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                            {service.name}
                          </h3>
                        </div>
                        <div className="flex items-center justify-between">
                          <Badge size="xs" className="bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400 text-[10px]">
                            Active
                          </Badge>
                          <span className="text-xs text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 font-medium transition-colors">
                            Manage →
                          </span>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* System Health */}
        <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 shadow-sm mt-8 mb-8">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            System Health
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {systemHealthMetrics.map((metric) => (
              <HealthMetric key={metric.label} label={metric.label} value={metric.value} status={metric.status} />
            ))}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

function QuickActionButton({ icon: Icon, label }: { icon: ComponentType<{ className?: string }>; label: string }) {
  return (
    <button className="flex flex-col items-center gap-1.5 p-3 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 hover:border-gray-200 dark:hover:border-gray-600 transition-all duration-200">
      <Icon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
      <span className="text-[11px] font-medium text-gray-700 dark:text-gray-300">{label}</span>
    </button>
  );
}

function HealthMetric({ label, value, status }: { label: string; value: string; status: 'healthy' | 'warning' | 'critical' }) {
  const statusColors = {
    healthy: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400',
    warning: 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400',
    critical: 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400',
  };

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</span>
        <Badge size="xs" className={`${statusColors[status]} text-[10px]`}>
          {status}
        </Badge>
      </div>
      <p className="text-xl font-bold text-gray-900 dark:text-white tabular-nums">{value}</p>
    </div>
  );
}
