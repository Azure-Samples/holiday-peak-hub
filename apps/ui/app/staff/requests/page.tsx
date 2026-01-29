'use client';

import React, { useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { Input } from '@/components/atoms/Input';
import { Select } from '@/components/atoms/Select';
import { Tabs } from '@/components/molecules/Tabs';
import { 
  FiPackage, FiClock, FiCheckCircle, FiXCircle,
  FiAlertCircle, FiSearch, FiFilter, FiMessageSquare
} from 'react-icons/fi';

export default function RequestsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Mock data
  const requests = [
    {
      id: 'REQ-001',
      type: 'Return',
      customer: 'John Doe',
      orderId: 'ORD-2026-0123',
      product: 'Wireless Headphones',
      status: 'pending',
      priority: 'high',
      created: '2 hours ago',
      description: 'Product arrived damaged, requesting return',
    },
    {
      id: 'REQ-002',
      type: 'Exchange',
      customer: 'Jane Smith',
      orderId: 'ORD-2026-0122',
      product: 'Smart Watch',
      status: 'in_progress',
      priority: 'medium',
      created: '5 hours ago',
      description: 'Wrong size received, need size exchange',
    },
    {
      id: 'REQ-003',
      type: 'Refund',
      customer: 'Mike Johnson',
      orderId: 'ORD-2026-0121',
      product: 'Laptop Backpack',
      status: 'resolved',
      priority: 'low',
      created: '1 day ago',
      description: 'Product not as described, requesting refund',
    },
    {
      id: 'REQ-004',
      type: 'Support',
      customer: 'Sarah Williams',
      orderId: 'ORD-2026-0120',
      product: 'Running Shoes',
      status: 'pending',
      priority: 'high',
      created: '3 hours ago',
      description: 'Unable to track order, need assistance',
    },
  ];

  const stats = [
    { label: 'Pending', count: 12, color: 'ocean' },
    { label: 'In Progress', count: 8, color: 'cyan' },
    { label: 'Resolved Today', count: 24, color: 'lime' },
    { label: 'Avg Response Time', count: '2.3h', color: 'ocean' },
  ];

  const getStatusBadge = (status: string) => {
    const configs = {
      pending: { label: 'Pending', className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300', icon: FiClock },
      in_progress: { label: 'In Progress', className: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300', icon: FiAlertCircle },
      resolved: { label: 'Resolved', className: 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300', icon: FiCheckCircle },
      rejected: { label: 'Rejected', className: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300', icon: FiXCircle },
    };
    const config = configs[status as keyof typeof configs] || configs.pending;
    const Icon = config.icon;
    return (
      <Badge className={config.className}>
        <Icon className="w-3 h-3 mr-1 inline" />
        {config.label}
      </Badge>
    );
  };

  const getPriorityBadge = (priority: string) => {
    const configs = {
      high: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
      medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
      low: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
    };
    return <Badge className={configs[priority as keyof typeof configs]}>{priority.toUpperCase()}</Badge>;
  };

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Customer Requests
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage returns, exchanges, and support tickets
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => (
            <Card key={stat.label} className="p-6">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{stat.label}</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{stat.count}</p>
            </Card>
          ))}
        </div>

        {/* Filters */}
        <Card className="p-6 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <Input
                  type="text"
                  placeholder="Search by request ID, customer, or order..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'pending', label: 'Pending' },
                { value: 'in_progress', label: 'In Progress' },
                { value: 'resolved', label: 'Resolved' },
              ]}
            />
            <Button variant="outline" className="border-ocean-500 text-ocean-500 dark:border-ocean-300 dark:text-ocean-300">
              <FiFilter className="mr-2 w-4 h-4" />
              More Filters
            </Button>
          </div>
        </Card>

        {/* Requests List */}
        <div className="space-y-4">
          {requests.map((request) => (
            <Card key={request.id} className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-ocean-100 dark:bg-ocean-900 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FiPackage className="w-6 h-6 text-ocean-500 dark:text-ocean-300" />
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        {request.id}
                      </h3>
                      {getStatusBadge(request.status)}
                      {getPriorityBadge(request.priority)}
                    </div>
                    <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
                      <p className="text-gray-600 dark:text-gray-400">
                        <span className="font-medium">Type:</span> {request.type}
                      </p>
                      <p className="text-gray-600 dark:text-gray-400">
                        <span className="font-medium">Customer:</span> {request.customer}
                      </p>
                      <p className="text-gray-600 dark:text-gray-400">
                        <span className="font-medium">Order:</span> {request.orderId}
                      </p>
                      <p className="text-gray-600 dark:text-gray-400">
                        <span className="font-medium">Created:</span> {request.created}
                      </p>
                    </div>
                    <p className="text-sm text-gray-900 dark:text-white mt-2">
                      <span className="font-medium">Product:</span> {request.product}
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                      {request.description}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" className="bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900">
                    <FiMessageSquare className="mr-1 w-4 h-4" />
                    Respond
                  </Button>
                  <Button size="sm" variant="outline">
                    View Details
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Pagination */}
        <div className="mt-8 flex justify-center">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">Previous</Button>
            <Button size="sm" className="bg-ocean-500 text-white">1</Button>
            <Button variant="outline" size="sm">2</Button>
            <Button variant="outline" size="sm">3</Button>
            <Button variant="outline" size="sm">Next</Button>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
