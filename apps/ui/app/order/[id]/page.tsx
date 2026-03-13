'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Badge } from '@/components/atoms/Badge';
import { Button } from '@/components/atoms/Button';
import { Input } from '@/components/atoms/Input';
import { useOrder } from '@/lib/hooks/useOrders';
import { useCreateReturn, useReturns } from '@/lib/hooks/useReturns';
import type { Return } from '@/lib/types/api';

const getReturnLifecycleMessage = (item: Return): string => {
  if (item.status === 'requested') {
    return 'Lifecycle: request submitted and waiting for staff review. Review SLA target is 24 hours.';
  }
  if (item.status === 'approved') {
    return 'Lifecycle: approved and waiting for item receipt.';
  }
  if (item.status === 'received') {
    return 'Lifecycle: item received and pending warehouse restock verification.';
  }
  if (item.status === 'restocked') {
    return 'Lifecycle: item restocked; refund processing SLA is up to 2 business days.';
  }
  if (item.status === 'refunded') {
    return 'Lifecycle: complete. Refund has been issued.';
  }

  return 'Lifecycle: request closed. No additional transitions are expected.';
};

const getReturnRefundMessage = (item: Return): string => {
  if (item.refund?.status === 'issued') {
    return 'Refund issued to the original payment method.';
  }
  if (item.status === 'rejected') {
    return 'Refund not applicable because the request was rejected.';
  }
  if (item.status === 'requested' || item.status === 'approved' || item.status === 'received') {
    return 'Refund is not yet eligible; processing starts after restock.';
  }
  if (item.status === 'restocked') {
    return 'Refund pending issuance; expected within 2 business days.';
  }

  return 'Refund status unavailable.';
};

export default function OrderTrackingPage() {
  const params = useParams<{ id: string }>();
  const orderId = params?.id || '';
  const { data: order, isLoading, isError } = useOrder(orderId);
  const { data: returns = [], isLoading: loadingReturns, isError: returnsError } = useReturns();
  const createReturnMutation = useCreateReturn();
  const [returnReason, setReturnReason] = useState('');

  const orderReturns = useMemo(
    () => returns.filter((item) => item.order_id === orderId),
    [returns, orderId],
  );

  const canCreateReturn = Boolean(order && returnReason.trim()) && !createReturnMutation.isPending;

  const onCreateReturn = async () => {
    if (!order || !returnReason.trim()) {
      return;
    }

    await createReturnMutation.mutateAsync({
      order_id: order.id,
      reason: returnReason.trim(),
      items: order.items.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
      })),
    });
    setReturnReason('');
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Order Details</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Track status, ETA and logistics enrichments for order {orderId}.</p>
        </div>

        {isLoading && (
          <Card className="p-6 text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
            Loading order details...
          </Card>
        )}

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

            <Card className="p-6 space-y-3">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Create Return</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Lifecycle starts at requested and moves through approved → received → restocked → refunded. Review target is within 24 hours;
                refund target is up to 2 business days after restock.
              </p>
              <Input
                type="text"
                placeholder="Reason for return"
                value={returnReason}
                onChange={(event) => setReturnReason(event.target.value)}
                ariaLabel="Reason for return request"
              />
              <div className="flex justify-end">
                <Button onClick={onCreateReturn} disabled={!canCreateReturn} loading={createReturnMutation.isPending}>
                  {createReturnMutation.isPending ? 'Creating return...' : 'Create Return'}
                </Button>
              </div>
              {createReturnMutation.isPending && (
                <p className="text-sm text-blue-700 dark:text-blue-300" role="status" aria-live="polite">
                  Creating return request and validating lifecycle eligibility...
                </p>
              )}
              {createReturnMutation.isSuccess && (
                <p className="text-sm text-green-700 dark:text-green-300" role="status" aria-live="polite">
                  Return request created. Staff review SLA target is 24 hours.
                </p>
              )}
              {createReturnMutation.isError && (
                <p className="text-sm text-red-600 dark:text-red-400" role="alert" aria-live="assertive">
                  Return could not be created. Verify order ownership and lifecycle constraints.
                </p>
              )}
            </Card>

            <Card className="overflow-x-auto">
              <h2 className="px-4 py-3 text-lg font-semibold text-gray-900 dark:text-white">Returns for this order</h2>
              <p className="px-4 pb-3 text-sm text-gray-600 dark:text-gray-400">
                Check lifecycle and refund progression per return. SLA reminders are shown in the status details.
              </p>
              {loadingReturns ? (
                <div className="px-4 pb-4 text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
                  Loading returns for this order...
                </div>
              ) : returnsError ? (
                <div className="px-4 pb-4 text-red-600 dark:text-red-400" role="alert" aria-live="assertive">
                  Returns could not be loaded.
                </div>
              ) : orderReturns.length === 0 ? (
                <div className="px-4 pb-4 text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
                  No returns requested for this order.
                </div>
              ) : (
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                    <tr>
                      <th className="px-4 py-3">Return</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Refund</th>
                      <th className="px-4 py-3">Requested</th>
                      <th className="px-4 py-3">Approved</th>
                      <th className="px-4 py-3">Received</th>
                      <th className="px-4 py-3">Restocked</th>
                      <th className="px-4 py-3">Refunded</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orderReturns.map((item) => (
                      <tr key={item.id} className="border-t border-gray-200 dark:border-gray-700">
                        <td className="px-4 py-3">
                          <p className="font-medium text-gray-900 dark:text-white">{item.id}</p>
                          <p className="text-xs text-gray-600 dark:text-gray-400">{item.reason}</p>
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-gray-900 dark:text-white">{item.status}</p>
                          <p className="text-xs text-gray-600 dark:text-gray-400">{getReturnLifecycleMessage(item)}</p>
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-gray-900 dark:text-white">{item.refund?.status ?? '-'}</p>
                          <p className="text-xs text-gray-600 dark:text-gray-400">{getReturnRefundMessage(item)}</p>
                        </td>
                        <td className="px-4 py-3">{new Date(item.requested_at).toLocaleString()}</td>
                        <td className="px-4 py-3">{item.approved_at ? new Date(item.approved_at).toLocaleString() : '-'}</td>
                        <td className="px-4 py-3">{item.received_at ? new Date(item.received_at).toLocaleString() : '-'}</td>
                        <td className="px-4 py-3">{item.restocked_at ? new Date(item.restocked_at).toLocaleString() : '-'}</td>
                        <td className="px-4 py-3">{item.refunded_at ? new Date(item.refunded_at).toLocaleString() : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </>
        )}
      </div>
    </MainLayout>
  );
}
