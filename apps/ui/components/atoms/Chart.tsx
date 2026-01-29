"use client";

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  BarChart,
  AreaChart,
  PieChart,
  Line,
  Bar,
  Area,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

export type ChartType = 'line' | 'bar' | 'horizontal-bar' | 'area' | 'pie' | 'donut';

export interface ChartDataPoint {
  [key: string]: string | number;
}

export interface ChartSeries {
  dataKey: string;
  name?: string;
  color: string;
}

export interface ChartProps {
  /** Type of chart to render */
  type: ChartType;
  /** Data array for the chart */
  data: ChartDataPoint[];
  /** Series configuration for multi-series charts */
  series: ChartSeries[];
  /** X-axis data key (for cartesian charts) */
  xAxisKey?: string;
  /** Chart height in pixels */
  height?: number;
  /** Show grid lines (for cartesian charts) */
  showGrid?: boolean;
  /** Show legend */
  showLegend?: boolean;
  /** Show tooltip */
  showTooltip?: boolean;
  /** Inner radius percentage (for donut charts, 0-100) */
  innerRadius?: number;
  /** Additional className for container */
  className?: string;
}

/**
 * Custom tooltip component with dark mode support
 */
const CustomTooltip: React.FC<{ active?: boolean; payload?: any }> = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  
  return (
    <div className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-lg rounded-lg p-3 border border-gray-200 dark:border-gray-700">
      {Object.entries(data).map(([key, value]) => {
        if (key === 'name' || typeof value !== 'number') {
          return key === 'name' ? (
            <div key={key} className="font-bold mb-1 text-sm">{value as string}</div>
          ) : null;
        }
        return (
          <div key={key} className="text-xs">
            <span className="font-semibold capitalize">{key}:</span>{' '}
            <span className="font-normal">{value}</span>
          </div>
        );
      })}
    </div>
  );
};

/**
 * Chart Atom Component
 * 
 * A versatile chart component supporting multiple visualization types:
 * - Line charts for trends over time
 * - Bar charts for categorical comparisons
 * - Area charts for cumulative data
 * - Pie/Donut charts for proportional data
 * 
 * Built with Recharts library and includes:
 * - Dark mode support
 * - Responsive sizing
 * - Interactive tooltips
 * - Customizable colors per series
 * 
 * @example
 * ```tsx
 * // Line chart example
 * <Chart
 *   type="line"
 *   data={[
 *     { month: 'Jan', sales: 100, revenue: 200 },
 *     { month: 'Feb', sales: 150, revenue: 250 },
 *   ]}
 *   series={[
 *     { dataKey: 'sales', name: 'Sales', color: '#3b82f6' },
 *     { dataKey: 'revenue', name: 'Revenue', color: '#ef4444' },
 *   ]}
 *   xAxisKey="month"
 *   height={300}
 *   showGrid
 *   showLegend
 * />
 * 
 * // Pie chart example
 * <Chart
 *   type="pie"
 *   data={[
 *     { name: 'Product A', value: 400 },
 *     { name: 'Product B', value: 300 },
 *   ]}
 *   series={[
 *     { dataKey: 'value', color: '#3b82f6' },
 *   ]}
 *   height={400}
 *   showLegend
 * />
 * ```
 */
export const Chart: React.FC<ChartProps> = ({
  type,
  data,
  series,
  xAxisKey = 'name',
  height = 300,
  showGrid = true,
  showLegend = true,
  showTooltip = true,
  innerRadius = 0,
  className = '',
}) => {
  const containerStyle = { width: '100%', height };

  // Render Cartesian charts (line, bar, area, horizontal-bar)
  if (type === 'line' || type === 'bar' || type === 'area' || type === 'horizontal-bar') {
    const isHorizontal = type === 'horizontal-bar';
    
    let ChartComponent: any;
    let DataComponent: any;
    
    switch (type) {
      case 'line':
        ChartComponent = LineChart;
        DataComponent = Line;
        break;
      case 'bar':
      case 'horizontal-bar':
        ChartComponent = BarChart;
        DataComponent = Bar;
        break;
      case 'area':
        ChartComponent = AreaChart;
        DataComponent = Area;
        break;
    }

    return (
      <div style={containerStyle} className={className}>
        <ResponsiveContainer>
          <ChartComponent
            data={data}
            layout={isHorizontal ? 'vertical' : 'horizontal'}
            margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
          >
            {showGrid && <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />}
            {isHorizontal ? (
              <>
                <XAxis type="number" axisLine={false} tickLine={false} className="text-xs text-gray-600 dark:text-gray-400" />
                <YAxis dataKey={xAxisKey} type="category" axisLine={false} tickLine={false} className="text-xs text-gray-600 dark:text-gray-400" />
              </>
            ) : (
              <>
                <XAxis dataKey={xAxisKey} axisLine={false} tickLine={false} className="text-xs text-gray-600 dark:text-gray-400" />
                <YAxis axisLine={false} tickLine={false} className="text-xs text-gray-600 dark:text-gray-400" />
              </>
            )}
            {showTooltip && <Tooltip content={<CustomTooltip />} />}
            {showLegend && <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />}
            {series.map((s) => (
              <DataComponent
                key={s.dataKey}
                dataKey={s.dataKey}
                name={s.name || s.dataKey}
                stroke={type === 'line' ? s.color : undefined}
                fill={type !== 'line' ? s.color : type === 'area' ? s.color : undefined}
                strokeWidth={type === 'line' ? 2 : undefined}
                fillOpacity={type === 'area' ? 0.6 : 1}
              />
            ))}
          </ChartComponent>
        </ResponsiveContainer>
      </div>
    );
  }

  // Render Pie/Donut charts
  if (type === 'pie' || type === 'donut') {
    const radiusValue = type === 'donut' ? innerRadius || 60 : 0;
    
    return (
      <div style={containerStyle} className={className}>
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={data}
              dataKey={series[0]?.dataKey || 'value'}
              nameKey="name"
              innerRadius={radiusValue}
              fill="#8884d8"
              label={!showLegend}
            >
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={series[index % series.length]?.color || '#3b82f6'} 
                />
              ))}
            </Pie>
            {showTooltip && <Tooltip content={<CustomTooltip />} />}
            {showLegend && (
              <Legend 
                align="right" 
                layout="vertical" 
                verticalAlign="middle" 
                iconType="circle"
                wrapperStyle={{ fontSize: '12px' }}
              />
            )}
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return null;
};

Chart.displayName = 'Chart';

export default Chart;
