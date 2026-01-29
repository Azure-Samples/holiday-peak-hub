'use client';

import React, { useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { Input } from '@/components/atoms/Input';
import { Timeline } from '@/components/molecules/Timeline';
import { 
  FiTruck, FiMapPin, FiClock, FiCheck, FiAlertCircle,
  FiPackage, FiSearch, FiNavigation
} from 'react-icons/fi';

export default function LogisticsTrackingPage() {
  const [searchQuery, setSearchQuery] = useState('');

  // Mock data
  const shipments = [
    {
      id: 'SHIP-001',
      orderId: 'ORD-2026-0123',
      customer: 'John Doe',
      carrier: 'FedEx',
      trackingNumber: 'FDX123456789',
      status: 'in_transit',
      origin: 'New York, NY',
      destination: 'Los Angeles, CA',
      estimatedDelivery: 'Jan 31, 2026',
      currentLocation: 'Chicago, IL',
      progress: 65,
    },
    {
      id: 'SHIP-002',
      orderId: 'ORD-2026-0122',
      customer: 'Jane Smith',
      carrier: 'UPS',
      trackingNumber: 'UPS987654321',
      status: 'out_for_delivery',
      origin: 'San Francisco, CA',
      destination: 'Seattle, WA',
      estimatedDelivery: 'Today',
      currentLocation: 'Seattle Distribution Center',
      progress: 90,
    },
    {
      id: 'SHIP-003',
      orderId: 'ORD-2026-0121',
      customer: 'Mike Johnson',
      carrier: 'USPS',
      trackingNumber: 'USPS456789123',
      status: 'delivered',
      origin: 'Boston, MA',
      destination: 'Miami, FL',
      estimatedDelivery: 'Jan 28, 2026',
      currentLocation: 'Delivered',
      progress: 100,
    },
    {
      id: 'SHIP-004',
      orderId: 'ORD-2026-0120',
      customer: 'Sarah Williams',
      carrier: 'FedEx',
      trackingNumber: 'FDX111222333',
      status: 'delayed',
      origin: 'Houston, TX',
      destination: 'Denver, CO',
      estimatedDelivery: 'Feb 2, 2026',
      currentLocation: 'Dallas, TX - Weather Delay',
      progress: 40,
    },
  ];

  const stats = [
    { label: 'Active Shipments', value: '156', color: 'ocean' },
    { label: 'Out for Delivery', value: '23', color: 'cyan' },
    { label: 'Delivered Today', value: '47', color: 'lime' },
    { label: 'Delayed', value: '8', color: 'red' },
  ];

  const getStatusBadge = (status: string) => {
    const configs = {
      in_transit: { label: 'In Transit', className: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300', icon: FiTruck },
      out_for_delivery: { label: 'Out for Delivery', className: 'bg-ocean-100 text-ocean-700 dark:bg-ocean-900 dark:text-ocean-300', icon: FiNavigation },
      delivered: { label: 'Delivered', className: 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300', icon: FiCheck },
      delayed: { label: 'Delayed', className: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300', icon: FiAlertCircle },
    };
    const config = configs[status as keyof typeof configs];
    const Icon = config.icon;
    return (
      <Badge className={config.className}>
        <Icon className="w-3 h-3 mr-1 inline" />
        {config.label}
      </Badge>
    );
  };

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Logistics Tracking
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Monitor and manage all shipments in real-time
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => (
            <Card key={stat.label} className="p-6">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{stat.label}</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
            </Card>
          ))}
        </div>

        {/* Search */}
        <Card className="p-6 mb-6">
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <Input
              type="text"
              placeholder="Search by shipment ID, tracking number, or order ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </Card>

        {/* Shipments List */}
        <div className="space-y-6">
          {shipments.map((shipment) => (
            <Card key={shipment.id} className="p-6">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      {shipment.id}
                    </h3>
                    {getStatusBadge(shipment.status)}
                  </div>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                    <p className="text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Order:</span> {shipment.orderId}
                    </p>
                    <p className="text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Customer:</span> {shipment.customer}
                    </p>
                    <p className="text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Carrier:</span> {shipment.carrier}
                    </p>
                    <p className="text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Tracking:</span> {shipment.trackingNumber}
                    </p>
                  </div>
                </div>
                <Button variant="outline" size="sm" className="border-ocean-500 text-ocean-500 dark:border-ocean-300 dark:text-ocean-300">
                  View Map
                </Button>
              </div>

              {/* Route */}
              <div className="mb-6">
                <div className="flex items-center justify-between text-sm mb-3">
                  <div className="flex items-center gap-2">
                    <FiMapPin className="w-4 h-4 text-ocean-500 dark:text-ocean-300" />
                    <span className="font-medium text-gray-900 dark:text-white">{shipment.origin}</span>
                  </div>
                  <div className="text-gray-600 dark:text-gray-400">
                    Current: {shipment.currentLocation}
                  </div>
                  <div className="flex items-center gap-2">
                    <FiMapPin className="w-4 h-4 text-lime-500 dark:text-lime-300" />
                    <span className="font-medium text-gray-900 dark:text-white">{shipment.destination}</span>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="relative">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-ocean-500 dark:bg-ocean-300 h-2 rounded-full transition-all"
                      style={{ width: `${shipment.progress}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between mt-2 text-xs text-gray-600 dark:text-gray-400">
                    <span>Shipped</span>
                    <span>{shipment.progress}%</span>
                    <span>ETA: {shipment.estimatedDelivery}</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <Button size="sm" className="bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900">
                  Update Status
                </Button>
                <Button size="sm" variant="outline">
                  Contact Carrier
                </Button>
                <Button size="sm" variant="outline">
                  Notify Customer
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
