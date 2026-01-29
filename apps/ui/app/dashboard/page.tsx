'use client';

import React from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { 
  FiPackage, FiHeart, FiUser, FiMapPin, FiCreditCard,
  FiShoppingBag, FiTruck, FiClock, FiCheck, FiArrowRight
} from 'react-icons/fi';

export default function DashboardPage() {
  // Mock data
  const stats = [
    { label: 'Total Orders', value: '24', icon: FiPackage, color: 'ocean' },
    { label: 'Wishlist Items', value: '12', icon: FiHeart, color: 'lime' },
    { label: 'Saved Addresses', value: '3', icon: FiMapPin, color: 'cyan' },
    { label: 'Rewards Points', value: '1,250', icon: FiShoppingBag, color: 'ocean' },
  ];

  const recentOrders = [
    {
      id: 'ORD-2026-0123',
      date: 'Jan 27, 2026',
      status: 'delivered',
      items: 2,
      total: 259.98,
    },
    {
      id: 'ORD-2026-0122',
      date: 'Jan 25, 2026',
      status: 'in_transit',
      items: 1,
      total: 89.99,
    },
    {
      id: 'ORD-2026-0121',
      date: 'Jan 20, 2026',
      status: 'processing',
      items: 3,
      total: 449.97,
    },
  ];

  const getStatusBadge = (status: string) => {
    const configs = {
      delivered: { label: 'Delivered', className: 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300' },
      in_transit: { label: 'In Transit', className: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300' },
      processing: { label: 'Processing', className: 'bg-ocean-100 text-ocean-700 dark:bg-ocean-900 dark:text-ocean-300' },
    };
    const config = configs[status as keyof typeof configs];
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            My Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Welcome back! Here's what's happening with your account.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => (
            <StatCard key={stat.label} {...stat} />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Recent Orders */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  Recent Orders
                </h2>
                <Link href="/orders">
                  <Button variant="outline" size="sm">
                    View All <FiArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </Link>
              </div>

              <div className="space-y-4">
                {recentOrders.map((order) => (
                  <div
                    key={order.id}
                    className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <Link
                          href={`/order/${order.id}`}
                          className="font-semibold text-ocean-500 dark:text-ocean-300 hover:underline"
                        >
                          {order.id}
                        </Link>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {order.date}
                        </p>
                      </div>
                      {getStatusBadge(order.status)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {order.items} item{order.items > 1 ? 's' : ''}
                      </span>
                      <span className="font-bold text-gray-900 dark:text-white">
                        ${order.total.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* Recommended Products */}
            <Card className="p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
                Recommended for You
              </h2>
              <div className="grid grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <RecommendedProduct key={i} id={i} />
                ))}
              </div>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Quick Actions
              </h3>
              <div className="space-y-3">
                <Link href="/orders">
                  <Button variant="outline" className="w-full justify-start">
                    <FiPackage className="mr-2" />
                    View All Orders
                  </Button>
                </Link>
                <Link href="/profile">
                  <Button variant="outline" className="w-full justify-start">
                    <FiUser className="mr-2" />
                    Edit Profile
                  </Button>
                </Link>
                <Link href="/wishlist">
                  <Button variant="outline" className="w-full justify-start">
                    <FiHeart className="mr-2" />
                    My Wishlist
                  </Button>
                </Link>
                <Link href="/addresses">
                  <Button variant="outline" className="w-full justify-start">
                    <FiMapPin className="mr-2" />
                    Manage Addresses
                  </Button>
                </Link>
              </div>
            </Card>

            {/* Rewards */}
            <Card className="p-6 bg-gradient-to-br from-ocean-50 to-cyan-50 dark:from-ocean-950 dark:to-cyan-950 border-ocean-200 dark:border-ocean-800">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-ocean-500 dark:bg-ocean-300 rounded-full flex items-center justify-center">
                  <FiShoppingBag className="w-6 h-6 text-white dark:text-gray-900" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white">
                    Rewards Program
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    1,250 points
                  </p>
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                You're 750 points away from your next reward!
              </p>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-4">
                <div className="bg-lime-500 h-2 rounded-full" style={{ width: '62%' }} />
              </div>
              <Button variant="outline" size="sm" className="w-full border-ocean-500 text-ocean-500 dark:border-ocean-300 dark:text-ocean-300">
                Learn More
              </Button>
            </Card>

            {/* Support */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Need Help?
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Our customer support team is here to assist you 24/7
              </p>
              <Link href="/help">
                <Button className="w-full bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900">
                  Contact Support
                </Button>
              </Link>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

function StatCard({ label, value, icon: Icon, color }: {
  label: string;
  value: string;
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
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{label}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
        </div>
        <div className={`w-14 h-14 rounded-full flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-7 h-7" />
        </div>
      </div>
    </Card>
  );
}

function RecommendedProduct({ id }: { id: number }) {
  return (
    <Link href={`/product/${id}`}>
      <div className="group cursor-pointer">
        <div className="aspect-square bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-lg mb-2 group-hover:scale-105 transition-transform" />
        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-1 line-clamp-2">
          Product {id}
        </h4>
        <p className="text-sm font-bold text-ocean-500 dark:text-ocean-300">
          ${(id * 49.99).toFixed(2)}
        </p>
      </div>
    </Link>
  );
}
