'use client';

import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { useStaffAnalyticsSummary } from '@/lib/hooks/useStaff';

export default function SalesAnalyticsPage() {
  const { data, isLoading, isError } = useStaffAnalyticsSummary();

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Sales Analytics</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Summary from /api/staff/analytics/summary.</p>
        </div>

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading analytics...</Card>}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Sales analytics could not be loaded.
          </Card>
        )}

        {data && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-6">
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Revenue</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">${data.total_revenue.toFixed(2)}</p>
              </Card>
              <Card className="p-6">
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Orders</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{data.total_orders}</p>
              </Card>
              <Card className="p-6">
                <p className="text-sm text-gray-600 dark:text-gray-400">Average Order Value</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">${data.average_order_value.toFixed(2)}</p>
              </Card>
            </div>

            <Card className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                  <tr>
                    <th className="px-4 py-3">Top Product</th>
                    <th className="px-4 py-3">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.top_products || []).map((entry, index) => {
                    const productName =
                      typeof entry.name === 'string' && entry.name.length > 0
                        ? entry.name
                        : typeof entry.id === 'string' && entry.id.length > 0
                        ? entry.id
                        : `Product ${index + 1}`;

                    return (
                      <tr key={`top-product-${index}`} className="border-t border-gray-200 dark:border-gray-700">
                        <td className="px-4 py-3">{productName}</td>
                        <td className="px-4 py-3">
                          <pre className="bg-gray-100 dark:bg-gray-800 p-2 rounded-lg overflow-x-auto">{JSON.stringify(entry, null, 2)}</pre>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {!data.top_products?.length && (
                <div className="p-6 text-gray-600 dark:text-gray-400">No top-product metrics available yet.</div>
              )}
            </Card>
          </>
        )}
      </div>
    </MainLayout>
  );
}
