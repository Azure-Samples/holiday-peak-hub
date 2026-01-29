'use client';

import React, { useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Button } from '@/components/atoms/Button';
import { Input } from '@/components/atoms/Input';
import { Card } from '@/components/molecules/Card';
import { Badge } from '@/components/atoms/Badge';
import { Timeline } from '@/components/molecules/Timeline';
import { 
  FiPackage, FiTruck, FiMapPin, FiCheck, 
  FiClock, FiArrowRight, FiPhone, FiMail 
} from 'react-icons/fi';

export default function OrderTrackingPage() {
  const [orderId, setOrderId] = useState('');
  const [email, setEmail] = useState('');
  const [orderFound, setOrderFound] = useState(false);

  // Mock order data - will be replaced with API call
  const order = {
    id: 'ORD-2026-0123456',
    status: 'in_transit',
    estimatedDelivery: 'January 31, 2026',
    items: [
      {
        id: 1,
        name: 'Wireless Headphones',
        quantity: 1,
        price: 199.99,
        image: '/placeholder.jpg',
      },
      {
        id: 2,
        name: 'Phone Case',
        quantity: 2,
        price: 29.99,
        image: '/placeholder.jpg',
      },
    ],
    shipping: {
      address: '123 Main St, New York, NY 10001',
      method: 'Express Shipping',
      carrier: 'FedEx',
      trackingNumber: 'FDX123456789',
    },
    timeline: [
      {
        title: 'Order Placed',
        description: 'Your order has been confirmed',
        timestamp: 'Jan 27, 2026 10:30 AM',
        status: 'completed',
      },
      {
        title: 'Processing',
        description: 'Preparing your items for shipment',
        timestamp: 'Jan 27, 2026 2:45 PM',
        status: 'completed',
      },
      {
        title: 'Shipped',
        description: 'Package handed to carrier',
        timestamp: 'Jan 28, 2026 9:00 AM',
        status: 'completed',
      },
      {
        title: 'In Transit',
        description: 'Package is on the way',
        timestamp: 'Jan 29, 2026 6:30 AM',
        status: 'active',
      },
      {
        title: 'Out for Delivery',
        description: 'Package is out for delivery',
        timestamp: 'Expected Jan 31',
        status: 'pending',
      },
      {
        title: 'Delivered',
        description: 'Package delivered',
        timestamp: 'Expected Jan 31',
        status: 'pending',
      },
    ],
  };

  const handleTrackOrder = (e: React.FormEvent) => {
    e.preventDefault();
    setOrderFound(true);
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { label: 'Pending', className: 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300' },
      processing: { label: 'Processing', className: 'bg-ocean-100 text-ocean-700 dark:bg-ocean-900 dark:text-ocean-300' },
      in_transit: { label: 'In Transit', className: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300' },
      delivered: { label: 'Delivered', className: 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300' },
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  if (!orderFound) {
    return (
      <MainLayout>
        <div className="max-w-2xl mx-auto py-12">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-ocean-100 dark:bg-ocean-900 rounded-full mb-4">
              <FiPackage className="w-8 h-8 text-ocean-500 dark:text-ocean-300" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Track Your Order
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Enter your order details to see real-time tracking information
            </p>
          </div>

          <Card className="p-8">
            <form onSubmit={handleTrackOrder} className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  Order ID
                </label>
                <Input
                  type="text"
                  placeholder="ORD-2026-0123456"
                  value={orderId}
                  onChange={(e) => setOrderId(e.target.value)}
                  required
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Found in your order confirmation email
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  Email Address
                </label>
                <Input
                  type="email"
                  placeholder="your.email@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <Button
                type="submit"
                size="lg"
                className="w-full bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900"
              >
                Track Order
                <FiArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </form>
          </Card>

          <div className="mt-8 text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Need help with your order?
            </p>
            <div className="flex flex-col sm:flex-row justify-center gap-4">
              <a
                href="tel:1-800-123-4567"
                className="inline-flex items-center text-ocean-500 dark:text-ocean-300 hover:underline"
              >
                <FiPhone className="mr-2 w-4 h-4" />
                1-800-123-4567
              </a>
              <a
                href="mailto:support@holidaypeak.com"
                className="inline-flex items-center text-ocean-500 dark:text-ocean-300 hover:underline"
              >
                <FiMail className="mr-2 w-4 h-4" />
                support@holidaypeak.com
              </a>
            </div>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-5xl mx-auto py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                Order Tracking
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Order {order.id}
              </p>
            </div>
            {getStatusBadge(order.status)}
          </div>
        </div>

        {/* Status Summary Card */}
        <Card className="p-6 mb-8 bg-gradient-to-r from-ocean-50 to-cyan-50 dark:from-ocean-950 dark:to-cyan-950 border-ocean-200 dark:border-ocean-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-ocean-500 dark:bg-ocean-300 rounded-full flex items-center justify-center">
                <FiTruck className="w-8 h-8 text-white dark:text-gray-900" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
                  Your Order is On the Way!
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  Estimated delivery: <span className="font-semibold text-ocean-600 dark:text-ocean-300">{order.estimatedDelivery}</span>
                </p>
              </div>
            </div>
          </div>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Timeline */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
                Tracking Timeline
              </h3>
              <Timeline
                items={order.timeline.map((item) => ({
                  id: item.title,
                  title: item.title,
                  description: item.description,
                  timestamp: item.timestamp,
                  status: item.status as 'completed' | 'active' | 'pending',
                }))}
              />
            </Card>

            {/* Order Items */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
                Items in this Order
              </h3>
              <div className="space-y-4">
                {order.items.map((item) => (
                  <div key={item.id} className="flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div className="w-20 h-20 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-600 rounded-lg flex-shrink-0" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900 dark:text-white mb-1">
                        {item.name}
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Quantity: {item.quantity}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-ocean-500 dark:text-ocean-300">
                        ${(item.price * item.quantity).toFixed(2)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Shipping Info */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <FiMapPin className="mr-2 text-ocean-500 dark:text-ocean-300" />
                Shipping Details
              </h3>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Delivery Address</p>
                  <p className="text-gray-900 dark:text-white">{order.shipping.address}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Shipping Method</p>
                  <p className="text-gray-900 dark:text-white">{order.shipping.method}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Carrier</p>
                  <p className="text-gray-900 dark:text-white">{order.shipping.carrier}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Tracking Number</p>
                  <p className="text-gray-900 dark:text-white font-mono">{order.shipping.trackingNumber}</p>
                </div>
              </div>
            </Card>

            {/* Quick Actions */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Need Help?
              </h3>
              <div className="space-y-3">
                <Button variant="outline" className="w-full justify-start">
                  <FiPhone className="mr-2" />
                  Contact Support
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <FiPackage className="mr-2" />
                  Return Item
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <FiMail className="mr-2" />
                  Report Issue
                </Button>
              </div>
            </Card>
          </div>
        </div>

        {/* Track Another Order */}
        <div className="mt-8 text-center">
          <Button
            variant="outline"
            onClick={() => setOrderFound(false)}
            className="border-ocean-500 text-ocean-500 hover:bg-ocean-50 dark:border-ocean-300 dark:text-ocean-300"
          >
            Track Another Order
          </Button>
        </div>
      </div>
    </MainLayout>
  );
}
