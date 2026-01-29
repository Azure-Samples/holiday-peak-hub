/**
 * OrderTracker Organism Component
 * Track order status and logistics with real-time updates
 */

import React from 'react';
import {
  FiPackage,
  FiTruck,
  FiCheck,
  FiClock,
  FiMapPin,
  FiAlertCircle,
} from 'react-icons/fi';
import { cn, formatCurrency } from '../utils';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { Text } from '../atoms/Text';
import { Divider } from '../atoms/Divider';
import { Alert } from '../molecules/Alert';
import type { Order, BaseComponentProps } from '../types';

export interface TrackingEvent {
  id: string;
  timestamp: string;
  status: string;
  location: string;
  description: string;
  completed: boolean;
}

export interface CarrierInfo {
  name: string;
  trackingNumber: string;
  trackingUrl?: string;
  estimatedDelivery: string;
}

export interface OrderTrackerProps extends BaseComponentProps {
  /** Order details */
  order: Order;
  /** Tracking events */
  trackingEvents?: TrackingEvent[];
  /** Carrier information */
  carrier?: CarrierInfo;
  /** ETA insights from logistics service */
  etaInsights?: {
    estimatedDelivery: string;
    confidence: 'high' | 'medium' | 'low';
    factors: string[];
  };
  /** Route issues from logistics service */
  routeIssues?: Array<{
    severity: 'error' | 'warning' | 'info';
    message: string;
    recommendation?: string;
  }>;
  /** Refresh tracking handler */
  onRefresh?: () => void;
  /** Contact support handler */
  onContactSupport?: () => void;
  /** Cancel order handler (if allowed) */
  onCancelOrder?: () => void;
  /** Loading state */
  loading?: boolean;
}

const orderStatusConfig = {
  pending: { label: 'Order Placed', icon: FiClock, color: 'bg-gray-500' },
  processing: { label: 'Processing', icon: FiPackage, color: 'bg-blue-500' },
  shipped: { label: 'Shipped', icon: FiTruck, color: 'bg-purple-500' },
  'out-for-delivery': { label: 'Out for Delivery', icon: FiTruck, color: 'bg-orange-500' },
  delivered: { label: 'Delivered', icon: FiCheck, color: 'bg-green-500' },
  cancelled: { label: 'Cancelled', icon: FiAlertCircle, color: 'bg-red-500' },
};

export const OrderTracker: React.FC<OrderTrackerProps> = ({
  order,
  trackingEvents = [],
  carrier,
  etaInsights,
  routeIssues = [],
  onRefresh,
  onContactSupport,
  onCancelOrder,
  loading = false,
  className,
  testId,
  ariaLabel,
}) => {
  const statusConfig = orderStatusConfig[order.status as keyof typeof orderStatusConfig] || orderStatusConfig.pending;
  const StatusIcon = statusConfig.icon;

  const canCancel = ['pending', 'processing'].includes(order.status);

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Order tracker'}
      className={cn('w-full', className)}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Tracking */}
        <div className="lg:col-span-2 space-y-6">
          {/* Order Header */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <Text variant="h3" className="mb-1">
                  Order #{order.orderNumber}
                </Text>
                <Text variant="caption" className="text-gray-500">
                  Placed on {new Date(order.createdAt).toLocaleDateString()}
                </Text>
              </div>
              <Badge
                variant={
                  order.status === 'delivered'
                    ? 'success'
                    : order.status === 'cancelled'
                    ? 'error'
                    : 'primary'
                }
              >
                {statusConfig.label}
              </Badge>
            </div>

            {/* Current Status Card */}
            <div className={cn('rounded-lg p-4', statusConfig.color)}>
              <div className="flex items-center gap-3 text-white">
                <StatusIcon className="w-8 h-8" />
                <div>
                  <Text variant="h4" className="text-white mb-1">
                    {statusConfig.label}
                  </Text>
                  {carrier && order.status !== 'pending' && (
                    <Text variant="caption" className="text-white/80">
                      {carrier.name} • {carrier.trackingNumber}
                    </Text>
                  )}
                </div>
              </div>
            </div>

            {/* ETA Insights */}
            {etaInsights && (
              <div className="mt-4">
                <Alert
                  variant={
                    etaInsights.confidence === 'high'
                      ? 'success'
                      : etaInsights.confidence === 'low'
                      ? 'warning'
                      : 'info'
                  }
                  title="Estimated Delivery"
                  borderLeft
                >
                  <div className="space-y-2">
                    <p className="font-semibold">
                      {new Date(etaInsights.estimatedDelivery).toLocaleDateString('en-US', {
                        weekday: 'long',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </p>
                    <p className="text-sm">
                      Confidence: {etaInsights.confidence}
                    </p>
                    {etaInsights.factors.length > 0 && (
                      <ul className="text-sm list-disc list-inside">
                        {etaInsights.factors.map((factor, i) => (
                          <li key={i}>{factor}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </Alert>
              </div>
            )}

            {/* Route Issues */}
            {routeIssues.length > 0 && (
              <div className="mt-4 space-y-3">
                {routeIssues.map((issue, index) => (
                  <Alert
                    key={index}
                    variant={issue.severity}
                    title="Delivery Update"
                  >
                    <p>{issue.message}</p>
                    {issue.recommendation && (
                      <p className="mt-1 font-semibold">{issue.recommendation}</p>
                    )}
                  </Alert>
                ))}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 mt-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={onRefresh}
                loading={loading}
              >
                Refresh Tracking
              </Button>
              {carrier?.trackingUrl && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => window.open(carrier.trackingUrl, '_blank')}
                >
                  Track with {carrier.name}
                </Button>
              )}
            </div>
          </div>

          {/* Tracking Timeline */}
          {trackingEvents.length > 0 && (
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <Text variant="h4" className="mb-4">Tracking History</Text>

              <div className="space-y-4">
                {trackingEvents.map((event, index) => (
                  <div key={event.id} className="flex gap-4">
                    {/* Timeline Dot */}
                    <div className="flex flex-col items-center">
                      <div
                        className={cn(
                          'w-3 h-3 rounded-full',
                          event.completed
                            ? 'bg-green-500'
                            : 'bg-gray-300 dark:bg-gray-600'
                        )}
                      />
                      {index < trackingEvents.length - 1 && (
                        <div className="w-0.5 h-full bg-gray-200 dark:bg-gray-700 mt-1" />
                      )}
                    </div>

                    {/* Event Details */}
                    <div className="flex-1 pb-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <Text variant="body" className="font-semibold mb-1">
                            {event.status}
                          </Text>
                          <Text variant="caption" className="text-gray-500 mb-1">
                            {new Date(event.timestamp).toLocaleString()}
                          </Text>
                          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                            <FiMapPin className="w-4 h-4" />
                            <span>{event.location}</span>
                          </div>
                          {event.description && (
                            <Text variant="caption" className="text-gray-600 dark:text-gray-400 mt-2">
                              {event.description}
                            </Text>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Order Items */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <Text variant="h4" className="mb-4">Order Items</Text>

            <div className="space-y-4">
              {order.items.map((item) => (
                <div key={item.sku} className="flex gap-4">
                  {item.image && (
                    <img
                      src={item.image}
                      alt={item.name}
                      className="w-20 h-20 object-cover rounded"
                    />
                  )}
                  <div className="flex-1">
                    <Text variant="body" className="font-semibold mb-1">
                      {item.name}
                    </Text>
                    <Text variant="caption" className="text-gray-500 mb-1">
                      SKU: {item.sku}
                    </Text>
                    <Text variant="caption" className="text-gray-600 dark:text-gray-400">
                      Qty: {item.quantity} × {formatCurrency(item.price, order.summary.currency)}
                    </Text>
                  </div>
                  <Text variant="body" className="font-semibold">
                    {formatCurrency(item.price * item.quantity, order.summary.currency)}
                  </Text>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Order Summary Sidebar */}
        <div className="lg:col-span-1">
          <div className="sticky top-4 space-y-6">
            {/* Shipping Address */}
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <Text variant="h4" className="mb-3">Shipping Address</Text>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <p>{order.shippingAddress.firstName} {order.shippingAddress.lastName}</p>
                <p>{order.shippingAddress.address}</p>
                <p>
                  {order.shippingAddress.city}, {order.shippingAddress.state}{' '}
                  {order.shippingAddress.zipCode}
                </p>
                <p>{order.shippingAddress.phone}</p>
              </div>
            </div>

            {/* Order Summary */}
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <Text variant="h4" className="mb-3">Order Summary</Text>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Subtotal</span>
                  <span>{formatCurrency(order.summary.subtotal, order.summary.currency)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Shipping</span>
                  <span>
                    {order.summary.shipping === 0
                      ? 'Free'
                      : formatCurrency(order.summary.shipping, order.summary.currency)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Tax</span>
                  <span>{formatCurrency(order.summary.tax, order.summary.currency)}</span>
                </div>
                {order.summary.discount > 0 && (
                  <div className="flex justify-between text-green-600 dark:text-green-400">
                    <span>Discount</span>
                    <span>-{formatCurrency(order.summary.discount, order.summary.currency)}</span>
                  </div>
                )}

                <Divider spacing="sm" />

                <div className="flex justify-between font-semibold text-base">
                  <span>Total</span>
                  <span>{formatCurrency(order.summary.total, order.summary.currency)}</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-3">
              {canCancel && onCancelOrder && (
                <Button
                  variant="error"
                  fullWidth
                  onClick={onCancelOrder}
                >
                  Cancel Order
                </Button>
              )}
              {onContactSupport && (
                <Button
                  variant="secondary"
                  fullWidth
                  onClick={onContactSupport}
                >
                  Contact Support
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

OrderTracker.displayName = 'OrderTracker';
