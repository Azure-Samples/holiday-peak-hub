'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Input } from '@/components/atoms/Input';
import { Badge } from '@/components/atoms/Badge';
import { useOrders } from '@/lib/hooks/useOrders';

export default function OrdersPage() {
  const { data: orders = [], isLoading, isError } = useOrders();
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return orders;
    }
    return orders.filter(
      (order) =>
        order.id.toLowerCase().includes(q) ||
        order.status.toLowerCase().includes(q)
    );
  }, [orders, query]);

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Orders</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Consult your order history from the CRUD backend.</p>
        </div>

        <Card className="p-4">
          <Input
            type="text"
            placeholder="Filter by order id or status"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </Card>

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading orders...</Card>}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Orders could not be loaded. Sign in and verify API connectivity.
          </Card>
        )}

        {!isLoading && !isError && (
          <Card className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                <tr>
                  <th className="px-4 py-3">Order</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Items</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((order) => (
                  <tr key={order.id} className="border-t border-gray-200 dark:border-gray-700">
                    <td className="px-4 py-3">
                      <Link className="text-ocean-500 dark:text-ocean-300 hover:underline" href={`/order/${encodeURIComponent(order.id)}`}>
                        {order.id}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className="bg-ocean-100 text-ocean-700 dark:bg-ocean-900 dark:text-ocean-300">
                        {order.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">{order.items.length}</td>
                    <td className="px-4 py-3 font-semibold">${order.total.toFixed(2)}</td>
                    <td className="px-4 py-3">{new Date(order.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="p-6 text-gray-600 dark:text-gray-400">No orders found.</div>
            )}
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
