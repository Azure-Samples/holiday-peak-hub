'use client';

import Link from 'next/link';
import { CommerceAgentLayout } from '@/components/templates/CommerceAgentLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { useCart, useClearCart, useRemoveFromCart } from '@/lib/hooks/useCart';

export default function CartPage() {
  const { data: cart, isLoading, isError } = useCart();
  const removeFromCart = useRemoveFromCart();
  const clearCart = useClearCart();
  const robotState = isLoading ? 'thinking' : cart?.items?.length ? 'talking' : 'idle';

  return (
    <CommerceAgentLayout
      primary={{
        agentSlug: 'ecommerce-cart-intelligence',
        state: robotState,
        position: 'bottom-left',
        size: 'sm',
        visible: true,
        facing: 'right',
        mode: 'lead',
      }}
      sideCast={[
        {
          agentSlug: 'inventory-reservation-validation',
          state: cart?.items?.length ? 'using-tool' : 'idle',
          position: 'bottom-right',
          size: 'sm',
          visible: Boolean(cart?.items?.length),
          facing: 'left',
          scenePeer: 'right',
          className: 'hidden xl:block',
          mode: 'observe',
        },
      ]}
      telemetry="compact"
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Cart</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">Review and edit cart items from the CRUD API.</p>
          </div>
          {cart?.items?.length ? (
            <Button variant="outline" onClick={() => clearCart.mutate()}>
              Clear cart
            </Button>
          ) : null}
        </div>

        {isLoading && <Card className="p-6 text-gray-600 dark:text-gray-400">Loading cart...</Card>}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Cart could not be loaded. Sign in and verify API connectivity.
          </Card>
        )}

        {!isLoading && !isError && (
          <Card className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <caption className="sr-only">Cart line items</caption>
              <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                <tr>
                  <th scope="col" className="px-4 py-3">Product</th>
                  <th scope="col" className="px-4 py-3">Quantity</th>
                  <th scope="col" className="px-4 py-3">Unit Price</th>
                  <th scope="col" className="px-4 py-3">Line Total</th>
                  <th scope="col" className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {cart?.items?.map((item) => (
                  <tr key={item.product_id} className="border-t border-gray-200 dark:border-gray-700">
                    <td className="px-4 py-3">
                      <Link className="text-[var(--hp-primary)] hover:text-[var(--hp-primary-hover)] hover:underline" href={`/product/${encodeURIComponent(item.product_id)}`}>
                        {item.product_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{item.quantity}</td>
                    <td className="px-4 py-3">${item.price.toFixed(2)}</td>
                    <td className="px-4 py-3 font-semibold">${(item.price * item.quantity).toFixed(2)}</td>
                    <td className="px-4 py-3">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => removeFromCart.mutate(item.product_id)}
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {!cart?.items?.length && (
              <div className="p-6 text-gray-600 dark:text-gray-400">Your cart is empty.</div>
            )}
          </Card>
        )}

        <Card className="p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Total</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">${(cart?.total || 0).toFixed(2)}</p>
          </div>
          <Link
            href="/checkout"
            className="inline-flex items-center justify-center rounded-xl bg-[var(--hp-primary)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--hp-primary-hover)]"
          >
            Proceed to checkout
          </Link>
        </Card>
      </div>
    </CommerceAgentLayout>
  );
}
