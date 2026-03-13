'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Input } from '@/components/atoms/Input';
import { Badge } from '@/components/atoms/Badge';
import { Button } from '@/components/atoms/Button';
import { useOrders } from '@/lib/hooks/useOrders';
import { useCreateReturn, useReturns } from '@/lib/hooks/useReturns';
import type { Order, Return } from '@/lib/types/api';

interface ReturnActionFeedback {
  orderId: string;
  type: 'success' | 'error';
  message: string;
}

const getOrderReturn = (orderId: string, returns: Return[]): Return | undefined => {
  const orderReturns = returns.filter((item) => item.order_id === orderId);
  if (orderReturns.length === 0) {
    return undefined;
  }

  return orderReturns.sort((a, b) => {
    return new Date(b.requested_at).getTime() - new Date(a.requested_at).getTime();
  })[0];
};

const hasOpenReturnLifecycle = (orderReturn?: Return): boolean => {
  if (!orderReturn) {
    return false;
  }

  return orderReturn.status !== 'rejected' && orderReturn.status !== 'refunded';
};

export default function OrdersPage() {
  const { data: orders = [], isLoading, isError } = useOrders();
  const { data: returns = [] } = useReturns();
  const createReturnMutation = useCreateReturn();
  const [query, setQuery] = useState('');
  const [pendingOrderId, setPendingOrderId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<ReturnActionFeedback | null>(null);

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

  const onRequestReturn = async (order: Order) => {
    if (createReturnMutation.isPending) {
      return;
    }

    setPendingOrderId(order.id);
    setFeedback(null);

    try {
      const payload = await createReturnMutation.mutateAsync({
        order_id: order.id,
        reason: 'Customer requested return from orders page',
        items: order.items.map((item) => ({
          product_id: item.product_id,
          quantity: item.quantity,
        })),
      });

      setFeedback({
        orderId: order.id,
        type: 'success',
        message: `Return ${payload.id} created with status ${payload.status}.`,
      });
    } catch {
      setFeedback({
        orderId: order.id,
        type: 'error',
        message: 'Return could not be requested. Verify lifecycle constraints and try again.',
      });
    } finally {
      setPendingOrderId(null);
    }
  };

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
                  <th className="px-4 py-3">Return</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((order) => {
                  const orderReturn = getOrderReturn(order.id, returns);
                  const hasOpenReturn = hasOpenReturnLifecycle(orderReturn);
                  const isPending = pendingOrderId === order.id;
                  const isDisabled = isPending || hasOpenReturn;

                  return (
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
                      <td className="px-4 py-3">
                        <div className="space-y-1">
                          <Button
                            size="sm"
                            variant="secondary"
                            loading={isPending}
                            disabled={isDisabled}
                            onClick={() => onRequestReturn(order)}
                            ariaLabel={`Request return for order ${order.id}`}
                          >
                            {isPending ? 'Requesting...' : 'Request Return'}
                          </Button>
                          {hasOpenReturn && orderReturn && (
                            <p className="text-xs text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
                              Return lifecycle in progress: {orderReturn.status}
                            </p>
                          )}
                          {feedback?.orderId === order.id && (
                            <p
                              className={feedback.type === 'success' ? 'text-xs text-green-700 dark:text-green-300' : 'text-xs text-red-600 dark:text-red-400'}
                              role={feedback.type === 'success' ? 'status' : 'alert'}
                              aria-live={feedback.type === 'success' ? 'polite' : 'assertive'}
                            >
                              {feedback.message}
                            </p>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
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
