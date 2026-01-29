/**
 * PriceDisplay Molecule Component
 * Displays product pricing with MSRP, sale price, and savings
 */

import React from 'react';
import { cn, formatCurrency, calculateSavingsPercent } from '../utils';
import { Badge } from '../atoms/Badge';
import type { BaseComponentProps } from '../types';

export interface PriceDisplayProps extends BaseComponentProps {
  /** Current price */
  price: number;
  /** Original/MSRP price (for showing discounts) */
  msrp?: number;
  /** Currency code */
  currency?: string;
  /** Locale for formatting */
  locale?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to show savings badge */
  showSavings?: boolean;
  /** Whether to show "Free" for zero price */
  showFree?: boolean;
  /** Custom label (e.g., "Starting at") */
  label?: string;
}

export const PriceDisplay: React.FC<PriceDisplayProps> = ({
  price,
  msrp,
  currency = 'USD',
  locale = 'en-US',
  size = 'md',
  showSavings = true,
  showFree = true,
  label,
  className,
  testId,
  ariaLabel,
}) => {
  const isOnSale = msrp && msrp > price;
  const savings = isOnSale ? calculateSavingsPercent(msrp, price) : 0;
  const isFree = price === 0;

  const sizeClasses = {
    sm: {
      price: 'text-lg',
      msrp: 'text-sm',
      label: 'text-xs',
    },
    md: {
      price: 'text-xl',
      msrp: 'text-base',
      label: 'text-sm',
    },
    lg: {
      price: 'text-2xl',
      msrp: 'text-lg',
      label: 'text-base',
    },
  };

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || `Price: ${formatCurrency(price, currency, locale)}`}
      className={cn('flex items-baseline gap-2 flex-wrap', className)}
    >
      {label && (
        <span className={cn('text-gray-600 dark:text-gray-400', sizeClasses[size].label)}>
          {label}
        </span>
      )}

      {isFree && showFree ? (
        <span className={cn('font-bold text-green-600 dark:text-green-400', sizeClasses[size].price)}>
          Free
        </span>
      ) : (
        <>
          <span
            className={cn(
              'font-bold',
              isOnSale
                ? 'text-red-600 dark:text-red-400'
                : 'text-gray-900 dark:text-white',
              sizeClasses[size].price
            )}
          >
            {formatCurrency(price, currency, locale)}
          </span>

          {isOnSale && (
            <>
              <span
                className={cn(
                  'text-gray-500 dark:text-gray-400 line-through',
                  sizeClasses[size].msrp
                )}
              >
                {formatCurrency(msrp!, currency, locale)}
              </span>

              {showSavings && savings > 0 && (
                <Badge variant="error" size={size === 'sm' ? 'sm' : 'md'}>
                  Save {savings}%
                </Badge>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
};

PriceDisplay.displayName = 'PriceDisplay';
