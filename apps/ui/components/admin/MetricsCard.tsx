'use client';

import React from 'react';
import { Card } from '@/components/molecules/Card';

interface MetricsCardProps {
  label: string;
  value: string | number;
  description?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  className?: string;
}

export function MetricsCard({ label, value, description, trend, trendValue, className }: MetricsCardProps) {
  const trendColors = {
    up: 'text-lime-600 dark:text-lime-400',
    down: 'text-red-600 dark:text-red-400',
    neutral: 'text-gray-500 dark:text-gray-400',
  };

  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→',
  };

  return (
    <Card className={`p-6 ${className ?? ''}`}>
      <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-900 dark:text-white mb-1">{value}</p>
      {description && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{description}</p>
      )}
      {trend && trendValue && (
        <span className={`text-sm font-medium ${trendColors[trend]}`}>
          {trendIcons[trend]} {trendValue}
        </span>
      )}
    </Card>
  );
}

export default MetricsCard;
