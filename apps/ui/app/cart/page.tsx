'use client';

import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { useCart, useClearCart, useRemoveFromCart } from '@/lib/hooks/useCart';

export default function CartPage() {
  const { data: cart, isLoading, isError } = useCart();
  const removeFromCart = useRemoveFromCart();
  const clearCart = useClearCart();

  return (
    <MainLayout>
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
              <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                <tr>
                  <th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">Quantity</th>
                  <th className="px-4 py-3">Unit Price</th>
                  <th className="px-4 py-3">Line Total</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {cart?.items?.map((item) => (
                  <tr key={item.product_id} className="border-t border-gray-200 dark:border-gray-700">
                    <td className="px-4 py-3">
                      <Link className="text-ocean-500 dark:text-ocean-300 hover:underline" href={`/product/${encodeURIComponent(item.product_id)}`}>
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
          <Link href="/checkout">
            <Button className="bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900">
              Proceed to checkout
            </Button>
          </Link>
        </Card>
      </div>
    </MainLayout>
  );
}
