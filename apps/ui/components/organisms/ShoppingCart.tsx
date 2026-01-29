/**
 * ShoppingCart Organism Component
 * Full shopping cart with items, summary, and checkout
 */

import React from 'react';
import { FiShoppingCart, FiArrowRight } from 'react-icons/fi';
import { cn, formatCurrency } from '../utils';
import { Button } from '../atoms/Button';
import { Badge } from '../atoms/Badge';
import { Divider } from '../atoms/Divider';
import { CartItem } from '../molecules/CartItem';
import { Alert } from '../molecules/Alert';
import type { CartItem as CartItemType, OrderSummary, CartInsights, BaseComponentProps } from '../types';

export interface ShoppingCartProps extends BaseComponentProps {
  /** Cart items */
  items: CartItemType[];
  /** Order summary */
  summary: OrderSummary;
  /** Cart intelligence insights (optional) */
  insights?: CartInsights;
  /** Quantity change handler */
  onQuantityChange?: (sku: string, quantity: number) => void;
  /** Remove item handler */
  onRemoveItem?: (sku: string) => void;
  /** Proceed to checkout handler */
  onCheckout?: () => void;
  /** Continue shopping handler */
  onContinueShopping?: () => void;
  /** Apply promo code handler */
  onApplyPromo?: (code: string) => void;
  /** Whether checkout button is disabled */
  checkoutDisabled?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Empty cart message */
  emptyMessage?: string;
}

export const ShoppingCart: React.FC<ShoppingCartProps> = ({
  items,
  summary,
  insights,
  onQuantityChange,
  onRemoveItem,
  onCheckout,
  onContinueShopping,
  onApplyPromo,
  checkoutDisabled = false,
  loading = false,
  emptyMessage = 'Your cart is empty',
  className,
  testId,
  ariaLabel,
}) => {
  const [promoCode, setPromoCode] = React.useState('');

  const handleApplyPromo = () => {
    if (promoCode.trim()) {
      onApplyPromo?.(promoCode.trim());
    }
  };

  // Empty cart
  if (items.length === 0 && !loading) {
    return (
      <div
        data-testid={testId}
        aria-label={ariaLabel || 'Shopping cart'}
        className={cn(
          'flex flex-col items-center justify-center py-16',
          className
        )}
      >
        <FiShoppingCart className="w-16 h-16 text-gray-400 mb-4" />
        <p className="text-lg text-gray-600 dark:text-gray-400 mb-6">
          {emptyMessage}
        </p>
        <Button
          variant="primary"
          size="lg"
          onClick={onContinueShopping}
        >
          Start Shopping
        </Button>
      </div>
    );
  }

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Shopping cart'}
      className={cn('w-full', className)}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cart Items */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Shopping Cart ({items.length} {items.length === 1 ? 'item' : 'items'})
          </h2>

          {/* AI Insights */}
          {insights && (
            <div className="space-y-3">
              {insights.abandonmentRisk !== 'low' && (
                <Alert
                  variant="warning"
                  title="Don't miss out!"
                  borderLeft
                >
                  {insights.insight}
                </Alert>
              )}

              {insights.stockWarnings.map((warning, index) => (
                <Alert
                  key={index}
                  variant={warning.severity === 'error' ? 'error' : 'warning'}
                >
                  {warning.message}
                </Alert>
              ))}

              {insights.priceDropAlerts.map((alert, index) => (
                <Alert
                  key={index}
                  variant="success"
                  title="Price Drop!"
                >
                  {alert.sku} is now ${alert.newPrice.toFixed(2)} (was ${alert.oldPrice.toFixed(2)}) - Save {alert.savingsPercent}%!
                </Alert>
              ))}
            </div>
          )}

          {/* Cart Items List */}
          <div className="space-y-4">
            {items.map((item) => (
              <CartItem
                key={item.sku}
                item={item}
                currency={summary.currency}
                onQuantityChange={onQuantityChange}
                onRemove={onRemoveItem}
                showMoveToWishlist
              />
            ))}
          </div>

          {/* Continue Shopping */}
          <Button
            variant="ghost"
            onClick={onContinueShopping}
          >
            Continue Shopping
          </Button>
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <div className="sticky top-4">
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Order Summary
              </h3>

              <Divider spacing="sm" />

              {/* Summary Lines */}
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Subtotal</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {formatCurrency(summary.subtotal, summary.currency)}
                  </span>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Shipping</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {summary.shipping === 0
                      ? 'Free'
                      : formatCurrency(summary.shipping, summary.currency)}
                  </span>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Tax</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {formatCurrency(summary.tax, summary.currency)}
                  </span>
                </div>

                {summary.discount > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-green-600 dark:text-green-400">Discount</span>
                    <span className="font-medium text-green-600 dark:text-green-400">
                      -{formatCurrency(summary.discount, summary.currency)}
                    </span>
                  </div>
                )}
              </div>

              {/* Promo Code */}
              <div className="space-y-2">
                <Divider spacing="sm" />
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Promo code"
                    value={promoCode}
                    onChange={(e) => setPromoCode(e.target.value)}
                    className={cn(
                      'flex-1 px-3 py-2 text-sm',
                      'border border-gray-300 dark:border-gray-700 rounded-md',
                      'bg-white dark:bg-gray-800',
                      'text-gray-900 dark:text-white',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500'
                    )}
                  />
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleApplyPromo}
                    disabled={!promoCode.trim()}
                  >
                    Apply
                  </Button>
                </div>
              </div>

              <Divider spacing="sm" />

              {/* Total */}
              <div className="flex justify-between items-baseline">
                <span className="text-lg font-semibold text-gray-900 dark:text-white">
                  Total
                </span>
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatCurrency(summary.total, summary.currency)}
                </span>
              </div>

              {/* Checkout Button */}
              <Button
                variant="primary"
                size="lg"
                fullWidth
                onClick={onCheckout}
                disabled={checkoutDisabled || loading}
                loading={loading}
                iconRight={<FiArrowRight className="w-5 h-5" />}
              >
                Proceed to Checkout
              </Button>

              {/* Security Badge */}
              <div className="flex items-center justify-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <Badge variant="success" size="sm">Secure</Badge>
                <span>SSL Encrypted</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

ShoppingCart.displayName = 'ShoppingCart';
