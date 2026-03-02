'use client';

import { useParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Badge } from '@/components/atoms/Badge';
import { useOrder } from '@/lib/hooks/useOrders';

export default function OrderTrackingPage() {
  const params = useParams<{ id: string }>();
  const orderId = params?.id || '';
  const { data: order, isLoading, isError } = useOrder(orderId);

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Order Details</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Track status, ETA and logistics enrichments for order {orderId}.</p>
        </div>

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading order...</Card>}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Order could not be loaded. Verify authentication and order access.
          </Card>
        )}

        {order && (
          <>
            <Card className="p-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Order ID</p>
                  <p className="text-xl font-bold text-gray-900 dark:text-white">{order.id}</p>
                </div>
                <Badge className="bg-ocean-100 text-ocean-700 dark:bg-ocean-900 dark:text-ocean-300">{order.status}</Badge>
              </div>
            </Card>

            <Card className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                  <tr>
                    <th className="px-4 py-3">Product</th>
                    <th className="px-4 py-3">Qty</th>
                    <th className="px-4 py-3">Unit Price</th>
                    <th className="px-4 py-3">Line Total</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items.map((item) => (
                    <tr key={item.product_id} className="border-t border-gray-200 dark:border-gray-700">
                      <td className="px-4 py-3">{item.product_id}</td>
                      <td className="px-4 py-3">{item.quantity}</td>
                      <td className="px-4 py-3">${item.price.toFixed(2)}</td>
                      <td className="px-4 py-3 font-semibold">${(item.price * item.quantity).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="p-6">
                <p className="text-sm text-gray-600 dark:text-gray-400">Order Total</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">${order.total.toFixed(2)}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">Created {new Date(order.created_at).toLocaleString()}</p>
              </Card>

              <Card className="p-6 lg:col-span-2">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Agent Enrichment</h2>
                <div className="space-y-3 text-sm">
                  {order.tracking ? (
                    <pre className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto">{JSON.stringify(order.tracking, null, 2)}</pre>
                  ) : (
                    <p className="text-gray-600 dark:text-gray-400">No tracking enrichment available.</p>
                  )}
                  {order.eta ? (
                    <pre className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto">{JSON.stringify(order.eta, null, 2)}</pre>
                  ) : null}
                  {order.carrier ? (
                    <pre className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto">{JSON.stringify(order.carrier, null, 2)}</pre>
                  ) : null}
                </div>
              </Card>
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );
}
