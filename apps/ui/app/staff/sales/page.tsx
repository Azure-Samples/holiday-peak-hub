'use client';

import React, { useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { Select } from '@/components/atoms/Select';
import { Chart } from '@/components/atoms/Chart';
import { 
  FiTrendingUp, FiDollarSign, FiShoppingCart, FiUsers,
  FiCalendar, FiDownload, FiFilter, FiRefreshCw
} from 'react-icons/fi';

export default function SalesAnalyticsPage() {
  const [timeRange, setTimeRange] = useState('7d');
  const [refreshing, setRefreshing] = useState(false);

  // Mock data - will be replaced with API calls
  const stats = [
    { 
      label: 'Total Revenue', 
      value: '$124,582', 
      change: '+12.5%', 
      trend: 'up',
      icon: FiDollarSign,
      color: 'ocean' 
    },
    { 
      label: 'Orders', 
      value: '1,847', 
      change: '+8.2%', 
      trend: 'up',
      icon: FiShoppingCart,
      color: 'lime' 
    },
    { 
      label: 'Avg Order Value', 
      value: '$67.45', 
      change: '+3.1%', 
      trend: 'up',
      icon: FiTrendingUp,
      color: 'cyan' 
    },
    { 
      label: 'New Customers', 
      value: '342', 
      change: '-2.4%', 
      trend: 'down',
      icon: FiUsers,
      color: 'ocean' 
    },
  ];

  const topProducts = [
    { name: 'Wireless Headphones', sales: 234, revenue: 46780 },
    { name: 'Smart Watch Pro', sales: 189, revenue: 66115 },
    { name: 'Laptop Backpack', sales: 156, revenue: 7794 },
    { name: 'Running Shoes', sales: 145, revenue: 13041 },
    { name: 'Phone Case', sales: 134, revenue: 4018 },
  ];

  const handleRefresh = async () => {
    setRefreshing(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setRefreshing(false);
  };

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Sales Analytics
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Real-time insights into your sales performance
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              options={[
                { value: '24h', label: 'Last 24 Hours' },
                { value: '7d', label: 'Last 7 Days' },
                { value: '30d', label: 'Last 30 Days' },
                { value: '90d', label: 'Last 90 Days' },
              ]}
            />
            <Button
              variant="outline"
              onClick={handleRefresh}
              disabled={refreshing}
              className="border-ocean-500 text-ocean-500 dark:border-ocean-300 dark:text-ocean-300"
            >
              <FiRefreshCw className={`mr-2 w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button className="bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900">
              <FiDownload className="mr-2 w-4 h-4" />
              Export Report
            </Button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => (
            <StatCard key={stat.label} {...stat} />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Charts */}
          <div className="lg:col-span-2 space-y-6">
            {/* Revenue Chart */}
            <Card className="p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
                Revenue Overview
              </h2>
              <div className="h-80 bg-gradient-to-br from-ocean-50 to-cyan-50 dark:from-ocean-950 dark:to-cyan-950 rounded-lg flex items-center justify-center">
                <p className="text-gray-500 dark:text-gray-400">Revenue Chart (will integrate with Chart component)</p>
              </div>
            </Card>

            {/* Orders Chart */}
            <Card className="p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
                Order Trends
              </h2>
              <div className="h-80 bg-gradient-to-br from-lime-50 to-green-50 dark:from-lime-950 dark:to-green-950 rounded-lg flex items-center justify-center">
                <p className="text-gray-500 dark:text-gray-400">Orders Chart (will integrate with Chart component)</p>
              </div>
            </Card>

            {/* Category Performance */}
            <Card className="p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
                Sales by Category
              </h2>
              <div className="space-y-4">
                {['Electronics', 'Fashion', 'Home & Garden', 'Sports', 'Books'].map((category, index) => {
                  const percentage = [45, 28, 15, 8, 4][index];
                  return (
                    <div key={category}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {category}
                        </span>
                        <span className="text-sm font-semibold text-ocean-500 dark:text-ocean-300">
                          {percentage}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-ocean-500 dark:bg-ocean-300 h-2 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Top Products */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Top Products
              </h3>
              <div className="space-y-4">
                {topProducts.map((product, index) => (
                  <div key={product.name} className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-lime-100 dark:bg-lime-900 rounded-full flex items-center justify-center">
                      <span className="text-sm font-bold text-lime-600 dark:text-lime-300">
                        {index + 1}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {product.name}
                      </p>
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        {product.sales} sales
                      </p>
                      <p className="text-sm font-semibold text-ocean-500 dark:text-ocean-300">
                        ${product.revenue.toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* Sales Goals */}
            <Card className="p-6 bg-gradient-to-br from-lime-50 to-green-50 dark:from-lime-950 dark:to-green-950 border-lime-200 dark:border-lime-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Monthly Goal
              </h3>
              <div className="text-center mb-4">
                <div className="text-4xl font-bold text-lime-600 dark:text-lime-300 mb-2">
                  82%
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  $164K / $200K
                </p>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-4">
                <div className="bg-lime-500 h-3 rounded-full" style={{ width: '82%' }} />
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400 text-center">
                Keep it up! Only $36K to reach your goal
              </p>
            </Card>

            {/* Quick Stats */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Quick Stats
              </h3>
              <div className="space-y-3">
                <QuickStat label="Conversion Rate" value="3.2%" />
                <QuickStat label="Avg Session Duration" value="4m 32s" />
                <QuickStat label="Cart Abandonment" value="68.5%" />
                <QuickStat label="Return Rate" value="2.1%" />
              </div>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

function StatCard({ label, value, change, trend, icon: Icon, color }: {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
  icon: React.ComponentType<{ className?: string }>;
  color: 'ocean' | 'lime' | 'cyan';
}) {
  const colorClasses = {
    ocean: 'bg-ocean-100 dark:bg-ocean-900 text-ocean-500 dark:text-ocean-300',
    lime: 'bg-lime-100 dark:bg-lime-900 text-lime-500 dark:text-lime-300',
    cyan: 'bg-cyan-100 dark:bg-cyan-900 text-cyan-500 dark:text-cyan-300',
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <Badge className={trend === 'up' ? 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300' : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'}>
          {change}
        </Badge>
      </div>
      <div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{label}</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
      </div>
    </Card>
  );
}

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
      <span className="text-sm font-semibold text-gray-900 dark:text-white">{value}</span>
    </div>
  );
}
