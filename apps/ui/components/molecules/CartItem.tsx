/**
 * CartItem Molecule Component
 * Shopping cart line item with quantity controls
 */

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { FiX, FiPlus, FiMinus } from 'react-icons/fi';
import { cn, formatCurrency } from '../utils';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import type { CartItem as CartItemType, BaseComponentProps } from '../types';

export interface CartItemProps extends BaseComponentProps {
  /** Cart item data */
  item: CartItemType;
  /** Whether to show remove button */
  showRemove?: boolean;
  /** Whether to show move to wishlist button */
  showMoveToWishlist?: boolean;
  /** Quantity change handler */
  onQuantityChange?: (sku: string, quantity: number) => void;
  /** Remove handler */
  onRemove?: (sku: string) => void;
  /** Move to wishlist handler */
  onMoveToWishlist?: (sku: string) => void;
  /** Currency code */
  currency?: string;
  /** Whether quantity controls are disabled */
  disableQuantityControls?: boolean;
  /** Compact layout (smaller) */
  compact?: boolean;
}

export const CartItem: React.FC<CartItemProps> = ({
  item,
  showRemove = true,
  showMoveToWishlist = false,
  onQuantityChange,
  onRemove,
  onMoveToWishlist,
  currency = 'USD',
  disableQuantityControls = false,
  compact = false,
  className,
  testId,
  ariaLabel,
}) => {
  const {
    sku,
    title,
    thumbnail,
    quantity,
    price,
    size,
    color,
    maxQuantity,
    inStock,
  } = item;

  const [localQuantity, setLocalQuantity] = useState(quantity);
  const isAtMax = maxQuantity ? localQuantity >= maxQuantity : false;
  const isAtMin = localQuantity <= 1;
  const subtotal = price * localQuantity;

  const handleIncrease = () => {
    if (!isAtMax && !disableQuantityControls) {
      const newQty = localQuantity + 1;
      setLocalQuantity(newQty);
      onQuantityChange?.(sku, newQty);
    }
  };

  const handleDecrease = () => {
    if (!isAtMin && !disableQuantityControls) {
      const newQty = localQuantity - 1;
      setLocalQuantity(newQty);
      onQuantityChange?.(sku, newQty);
    }
  };

  const handleRemove = () => {
    onRemove?.(sku);
  };

  const handleMoveToWishlist = () => {
    onMoveToWishlist?.(sku);
  };

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || `Cart item: ${title}`}
      className={cn(
        'flex gap-4',
        compact ? 'p-3' : 'p-4',
        'bg-white dark:bg-gray-800',
        'border border-gray-200 dark:border-gray-700',
        'rounded-lg',
        !inStock && 'opacity-75',
        className
      )}
    >
      {/* Image */}
      <Link
        href={`/products/${sku}`}
        className={cn(
          'shrink-0 relative overflow-hidden rounded-md',
          compact ? 'w-16 h-16' : 'w-24 h-24'
        )}
      >
        <Image
          src={thumbnail}
          alt={title}
          fill
          className="object-cover"
        />
        {!inStock && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <Badge variant="error" size="sm">Out of Stock</Badge>
          </div>
        )}
      </Link>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <Link
              href={`/products/${sku}`}
              className={cn(
                'block font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400',
                compact ? 'text-sm' : 'text-base',
                'line-clamp-2'
              )}
            >
              {title}
            </Link>

            {/* Variants */}
            {(size || color) && (
              <div className={cn('flex gap-2 mt-1', compact ? 'text-xs' : 'text-sm')}>
                {size && (
                  <span className="text-gray-500 dark:text-gray-400">
                    Size: {size}
                  </span>
                )}
                {color && (
                  <span className="text-gray-500 dark:text-gray-400">
                    Color: {color}
                  </span>
                )}
              </div>
            )}

            {/* Stock Warning */}
            {!inStock && (
              <Badge variant="error" size="sm" className="mt-2">
                Out of Stock
              </Badge>
            )}
          </div>

          {/* Remove Button */}
          {showRemove && (
            <button
              type="button"
              onClick={handleRemove}
              className="p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
              aria-label="Remove item"
            >
              <FiX className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Quantity & Price */}
        <div className="flex items-center justify-between mt-3">
          {/* Quantity Controls */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDecrease}
              disabled={isAtMin || disableQuantityControls || !inStock}
              className={cn(
                'p-1 rounded border border-gray-300 dark:border-gray-700',
                'hover:bg-gray-100 dark:hover:bg-gray-700',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-colors'
              )}
              aria-label="Decrease quantity"
            >
              <FiMinus className="w-4 h-4" />
            </button>

            <span
              className={cn(
                'font-medium text-gray-900 dark:text-white min-w-[2rem] text-center',
                compact ? 'text-sm' : 'text-base'
              )}
            >
              {localQuantity}
            </span>

            <button
              type="button"
              onClick={handleIncrease}
              disabled={isAtMax || disableQuantityControls || !inStock}
              className={cn(
                'p-1 rounded border border-gray-300 dark:border-gray-700',
                'hover:bg-gray-100 dark:hover:bg-gray-700',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-colors'
              )}
              aria-label="Increase quantity"
            >
              <FiPlus className="w-4 h-4" />
            </button>

            {maxQuantity && (
              <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                Max: {maxQuantity}
              </span>
            )}
          </div>

          {/* Subtotal */}
          <div className="text-right">
            <p className={cn('font-bold text-gray-900 dark:text-white', compact ? 'text-base' : 'text-lg')}>
              {formatCurrency(subtotal, currency)}
            </p>
            {localQuantity > 1 && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {formatCurrency(price, currency)} each
              </p>
            )}
          </div>
        </div>

        {/* Actions */}
        {showMoveToWishlist && (
          <div className="mt-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleMoveToWishlist}
            >
              Move to Wishlist
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

CartItem.displayName = 'CartItem';
