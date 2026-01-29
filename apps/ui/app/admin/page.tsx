'use client';

import React from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { 
  FiShoppingCart, FiPackage, FiTruck, FiUsers, FiTrendingUp,
  FiDatabase, FiLayers, FiSettings, FiShield, FiBarChart2,
  FiActivity, FiCpu, FiServer, FiTool, FiGlobe, FiList,
  FiBox, FiTag, FiGrid, FiCheckSquare, FiFileText, FiClock,
  FiMapPin
} from 'react-icons/fi';

export default function AdminPortalPage() {
  const serviceCategories = [
    {
      name: 'CRM Services',
      description: 'Customer relationship management and personalization',
      services: [
        { name: 'Campaign Intelligence', icon: FiTrendingUp, url: '/admin/crm/campaigns' },
        { name: 'Profile Aggregation', icon: FiUsers, url: '/admin/crm/profiles' },
        { name: 'Segmentation', icon: FiGrid, url: '/admin/crm/segmentation' },
        { name: 'Support Assistance', icon: FiShield, url: '/admin/crm/support' },
      ],
    },
    {
      name: 'E-Commerce Services',
      description: 'Product catalog, cart, and order management',
      services: [
        { name: 'Catalog Search', icon: FiShoppingCart, url: '/admin/ecommerce/catalog' },
        { name: 'Cart Intelligence', icon: FiShoppingCart, url: '/admin/ecommerce/cart' },
        { name: 'Checkout Support', icon: FiCheckSquare, url: '/admin/ecommerce/checkout' },
        { name: 'Order Status', icon: FiPackage, url: '/admin/ecommerce/orders' },
        { name: 'Product Enrichment', icon: FiTag, url: '/admin/ecommerce/products' },
      ],
    },
    {
      name: 'Inventory Services',
      description: 'Stock management and optimization',
      services: [
        { name: 'Health Check', icon: FiActivity, url: '/admin/inventory/health' },
        { name: 'Alerts & Triggers', icon: FiActivity, url: '/admin/inventory/alerts' },
        { name: 'JIT Replenishment', icon: FiBox, url: '/admin/inventory/replenishment' },
        { name: 'Reservation Validation', icon: FiCheckSquare, url: '/admin/inventory/reservation' },
      ],
    },
    {
      name: 'Logistics Services',
      description: 'Shipping and delivery optimization',
      services: [
        { name: 'Carrier Selection', icon: FiTruck, url: '/admin/logistics/carriers' },
        { name: 'ETA Computation', icon: FiClock, url: '/admin/logistics/eta' },
        { name: 'Returns Support', icon: FiPackage, url: '/admin/logistics/returns' },
        { name: 'Route Issue Detection', icon: FiMapPin, url: '/admin/logistics/routes' },
      ],
    },
    {
      name: 'Product Management',
      description: 'Product data and catalog management',
      services: [
        { name: 'ACP Transformation', icon: FiFileText, url: '/admin/products/acp' },
        { name: 'Assortment Optimization', icon: FiGrid, url: '/admin/products/assortment' },
        { name: 'Consistency Validation', icon: FiCheckSquare, url: '/admin/products/validation' },
        { name: 'Normalization', icon: FiLayers, url: '/admin/products/normalization' },
      ],
    },
  ];

  const systemStats = [
    { label: 'Active Services', value: '21', icon: FiServer, color: 'ocean' },
    { label: 'API Calls (24h)', value: '1.2M', icon: FiActivity, color: 'lime' },
    { label: 'Uptime', value: '99.9%', icon: FiCheckSquare, color: 'cyan' },
    { label: 'Avg Response', value: '120ms', icon: FiCpu, color: 'ocean' },
  ];

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Admin Portal
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Central hub for managing all backend services and system operations
          </p>
        </div>

        {/* System Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {systemStats.map((stat) => {
            const Icon = stat.icon;
            return (
              <Card key={stat.label} className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-ocean-100 dark:bg-ocean-900 rounded-full flex items-center justify-center">
                    <Icon className="w-6 h-6 text-ocean-500 dark:text-ocean-300" />
                  </div>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
              </Card>
            );
          })}
        </div>

        {/* Quick Actions */}
        <Card className="p-6 mb-8 bg-gradient-to-r from-ocean-50 to-cyan-50 dark:from-ocean-950 dark:to-cyan-950 border-ocean-200 dark:border-ocean-800">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Quick Actions
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <QuickActionButton icon={FiBarChart2} label="Analytics" />
            <QuickActionButton icon={FiSettings} label="Settings" />
            <QuickActionButton icon={FiDatabase} label="Database" />
            <QuickActionButton icon={FiShield} label="Security" />
            <QuickActionButton icon={FiTool} label="Tools" />
            <QuickActionButton icon={FiGlobe} label="API Docs" />
          </div>
        </Card>

        {/* Service Categories */}
        <div className="space-y-8">
          {serviceCategories.map((category) => (
            <div key={category.name}>
              <div className="mb-4">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  {category.name}
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  {category.description}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {category.services.map((service) => {
                  const Icon = service.icon;
                  return (
                    <Link key={service.name} href={service.url}>
                      <Card className="p-6 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 cursor-pointer">
                        <div className="flex items-center gap-4 mb-4">
                          <div className="w-12 h-12 bg-ocean-100 dark:bg-ocean-900 rounded-lg flex items-center justify-center flex-shrink-0">
                            <Icon className="w-6 h-6 text-ocean-500 dark:text-ocean-300" />
                          </div>
                          <h3 className="font-semibold text-gray-900 dark:text-white">
                            {service.name}
                          </h3>
                        </div>
                        <div className="flex items-center justify-between">
                          <Badge className="bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300 text-xs">
                            Active
                          </Badge>
                          <span className="text-sm text-ocean-500 dark:text-ocean-300 font-medium">
                            Manage →
                          </span>
                        </div>
                      </Card>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* System Health */}
        <Card className="p-6 mt-8">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
            System Health Monitor
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <HealthMetric label="Memory Usage" value="68%" status="healthy" />
            <HealthMetric label="CPU Load" value="42%" status="healthy" />
            <HealthMetric label="API Latency" value="120ms" status="healthy" />
            <HealthMetric label="Error Rate" value="0.02%" status="healthy" />
            <HealthMetric label="Queue Depth" value="234" status="warning" />
            <HealthMetric label="Cache Hit Rate" value="94%" status="healthy" />
          </div>
        </Card>
      </div>
    </MainLayout>
  );
}

function QuickActionButton({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>; label: string }) {
  return (
    <button className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 rounded-lg border-2 border-transparent hover:border-ocean-500 dark:hover:border-ocean-300 transition-colors">
      <Icon className="w-6 h-6 text-ocean-500 dark:text-ocean-300" />
      <span className="text-sm font-medium text-gray-900 dark:text-white">{label}</span>
    </button>
  );
}

function HealthMetric({ label, value, status }: { label: string; value: string; status: 'healthy' | 'warning' | 'critical' }) {
  const statusColors = {
    healthy: 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300',
    warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    critical: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  };

  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</span>
        <Badge className={`${statusColors[status]} text-xs`}>
          {status.toUpperCase()}
        </Badge>
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}
