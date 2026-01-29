"use client";

import React from 'react';

export interface StatCardProps {
  /** Title/label for the stat */
  title: React.ReactNode;
  /** Value/description (can be number or formatted string) */
  value: React.ReactNode;
  /** Optional content on the right side (icon, chart, etc.) */
  rightContent?: React.ReactNode;
  /** Additional className for container */
  className?: string;
}

/**
 * StatCard Molecule Component
 * 
 * A card designed for displaying statistics and metrics.
 * Perfect for dashboard widgets showing KPIs, metrics, or key data points.
 * 
 * Features:
 * - Dark mode support
 * - Optional right-side content (icons, mini charts)
 * - Flexible title and value rendering
 * - Consistent border and background styling
 * 
 * @example
 * ```tsx
 * // Basic stat
 * <StatCard
 *   title="Total Revenue"
 *   value="$45,231"
 * />
 * 
 * // With icon
 * <StatCard
 *   title="Active Users"
 *   value="1,247"
 *   rightContent={<FiUsers className="w-8 h-8 text-blue-500" />}
 * />
 * 
 * // With trend indicator
 * <StatCard
 *   title="Conversion Rate"
 *   value={
 *     <div>
 *       <span className="text-2xl font-bold">3.24%</span>
 *       <span className="ml-2 text-sm text-green-500">↑ 12%</span>
 *     </div>
 *   }
 * />
 * 
 * // With mini chart
 * <StatCard
 *   title="Sales Trend"
 *   value="Last 7 days"
 *   rightContent={<MiniLineChart data={salesData} />}
 * />
 * ```
 */
export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  rightContent,
  className = '',
}) => {
  return (
    <div 
      className={`w-full p-4 rounded-lg bg-white border border-gray-100 dark:bg-gray-900 dark:border-gray-800 ${className}`}
    >
      <div className="flex flex-row items-center justify-between">
        <div className="flex flex-col">
          <div className="text-xs font-light text-gray-500 uppercase">
            {title}
          </div>
          <div className="text-xl font-bold">{value}</div>
        </div>
        {rightContent && (
          <div className="flex-shrink-0 ml-4">
            {rightContent}
          </div>
        )}
      </div>
    </div>
  );
};

StatCard.displayName = 'StatCard';

export default StatCard;
