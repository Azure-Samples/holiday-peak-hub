/**
 * CheckoutLayout Template
 * Multi-step checkout process layout
 */

import React from 'react';
import { cn } from '../utils';
import { CheckoutForm } from '../organisms/CheckoutForm';
import type {
  CheckoutFormProps,
  BaseComponentProps,
} from '../types';

export interface CheckoutLayoutProps extends Omit<CheckoutFormProps, 'className'>, BaseComponentProps {
  /** Header content (optional) */
  header?: React.ReactNode;
  /** Show secure checkout badge */
  showSecureBadge?: boolean;
}

export const CheckoutLayout: React.FC<CheckoutLayoutProps> = ({
  header,
  showSecureBadge = true,
  className,
  testId,
  ariaLabel,
  ...checkoutFormProps
}) => {
  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Checkout layout'}
      className={cn(
        'w-full min-h-screen bg-gray-50 dark:bg-gray-900 py-8',
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        {header && (
          <div className="mb-8">
            {header}
          </div>
        )}

        {/* Secure Checkout Badge */}
        {showSecureBadge && (
          <div className="flex items-center justify-center gap-2 mb-6 text-sm text-gray-600 dark:text-gray-400">
            <svg
              className="w-5 h-5 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
            <span>Secure Checkout • SSL Encrypted</span>
          </div>
        )}

        {/* Checkout Form */}
        <CheckoutForm {...checkoutFormProps} />
      </div>
    </div>
  );
};

CheckoutLayout.displayName = 'CheckoutLayout';
