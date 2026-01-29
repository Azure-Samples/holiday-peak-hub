/**
 * OrderTrackingLayout Template
 * Order tracking and status page layout
 */

import React from 'react';
import { cn } from '../utils';
import { OrderTracker } from '../organisms/OrderTracker';
import type {
  OrderTrackerProps,
  BaseComponentProps,
} from '../types';

export interface OrderTrackingLayoutProps extends Omit<OrderTrackerProps, 'className'>, BaseComponentProps {
  /** Header content (optional) */
  header?: React.ReactNode;
  /** Breadcrumb or back navigation */
  breadcrumb?: React.ReactNode;
}

export const OrderTrackingLayout: React.FC<OrderTrackingLayoutProps> = ({
  header,
  breadcrumb,
  className,
  testId,
  ariaLabel,
  ...orderTrackerProps
}) => {
  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Order tracking layout'}
      className={cn(
        'w-full min-h-screen bg-gray-50 dark:bg-gray-900 py-8',
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        {breadcrumb && (
          <div className="mb-6">
            {breadcrumb}
          </div>
        )}

        {/* Header */}
        {header && (
          <div className="mb-8">
            {header}
          </div>
        )}

        {/* Order Tracker */}
        <OrderTracker {...orderTrackerProps} />
      </div>
    </div>
  );
};

OrderTrackingLayout.displayName = 'OrderTrackingLayout';
