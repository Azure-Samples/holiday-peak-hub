'use client';

import React from 'react';
import { Chart } from '@/components/atoms/Chart';
import { Card } from '@/components/molecules/Card';
import type { CompletenessBreakdown } from '@/lib/types/api';

interface CompletenessChartProps {
  data: CompletenessBreakdown[];
  isLoading?: boolean;
  className?: string;
}

export function CompletenessChart({ data, isLoading, className }: CompletenessChartProps) {
  const chartData = data.map((item) => ({
    category: item.category,
    completeness: Math.round(item.completeness * 100),
    products: item.product_count,
  }));

  return (
    <Card className={`p-6 ${className ?? ''}`}>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Completeness by Category
      </h3>
      {isLoading ? (
        <div className="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
          Loading chart...
        </div>
      ) : data.length === 0 ? (
        <div className="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
          No data available
        </div>
      ) : (
        <Chart
          type="horizontal-bar"
          data={chartData}
          series={[{ dataKey: 'completeness', name: 'Completeness (%)', color: '#0ea5e9' }]}
          xAxisKey="category"
          height={300}
          showGrid
          showTooltip
          showLegend={false}
        />
      )}
    </Card>
  );
}

export default CompletenessChart;
