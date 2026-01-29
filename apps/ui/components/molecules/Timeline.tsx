"use client";

import React from 'react';

export interface TimelineItemData {
  /** Item title */
  title: string;
  /** Item description/sentence */
  description?: string;
  /** Timestamp or relative time */
  timestamp?: string;
  /** Optional icon or custom marker */
  icon?: React.ReactNode;
  /** Optional badge/status */
  status?: React.ReactNode;
}

export interface TimelineProps {
  /** Array of timeline items */
  items: TimelineItemData[];
  /** Marker type */
  markerType?: 'number' | 'dot' | 'icon';
  /** Marker color */
  markerColor?: string;
  /** Line color */
  lineColor?: string;
  /** Additional className */
  className?: string;
}

/**
 * Timeline Molecule Component
 * 
 * A vertical timeline component for displaying chronological events.
 * Perfect for activity feeds, order tracking, project milestones, and history logs.
 * 
 * Features:
 * - Dark mode support
 * - Configurable markers (numbered, dots, or icons)
 * - Vertical connecting line
 * - Optional timestamps and status badges
 * - Flexible content layout
 * 
 * @example
 * ```tsx
 * // Numbered timeline
 * <Timeline
 *   items={[
 *     {
 *       title: 'Order Placed',
 *       description: 'Your order has been received',
 *       timestamp: '2 hours ago',
 *     },
 *     {
 *       title: 'Payment Confirmed',
 *       description: 'Payment processing complete',
 *       timestamp: '1 hour ago',
 *     },
 *     {
 *       title: 'Shipped',
 *       description: 'Package is on the way',
 *       timestamp: '30 min ago',
 *     },
 *   ]}
 *   markerType="number"
 * />
 * 
 * // Icon-based timeline
 * <Timeline
 *   items={[
 *     {
 *       title: 'Account Created',
 *       timestamp: 'Jan 1, 2026',
 *       icon: <FiUser />,
 *     },
 *     {
 *       title: 'First Purchase',
 *       timestamp: 'Jan 5, 2026',
 *       icon: <FiShoppingCart />,
 *     },
 *     {
 *       title: 'Review Posted',
 *       timestamp: 'Jan 10, 2026',
 *       icon: <FiStar />,
 *     },
 *   ]}
 *   markerType="icon"
 * />
 * 
 * // With status badges
 * <Timeline
 *   items={[
 *     {
 *       title: 'Task 1',
 *       description: 'Completed successfully',
 *       timestamp: 'Yesterday',
 *       status: <Badge variant="success">Done</Badge>,
 *     },
 *     {
 *       title: 'Task 2',
 *       description: 'Currently in progress',
 *       timestamp: 'Today',
 *       status: <Badge variant="warning">In Progress</Badge>,
 *     },
 *   ]}
 * />
 * ```
 */
export const Timeline: React.FC<TimelineProps> = ({
  items,
  markerType = 'number',
  markerColor = 'bg-blue-500',
  lineColor = 'bg-gray-200 dark:bg-gray-700',
  className = '',
}) => {
  return (
    <div className={`flex flex-col w-full ${className}`}>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        
        return (
          <div key={index} className="flex relative justify-start items-start">
            {/* Vertical Line */}
            {!isLast && (
              <div className="absolute inset-0 flex items-center justify-center w-6 h-full">
                <div className={`w-1 h-full ${lineColor} pointer-events-none`} />
              </div>
            )}

            {/* Marker */}
            <div className="relative z-10 shrink-0">
              {markerType === 'number' && (
                <div
                  className={`inline-flex items-center justify-center w-6 h-6 text-sm font-medium text-white ${markerColor} rounded-full`}
                >
                  {index + 1}
                </div>
              )}
              {markerType === 'dot' && (
                <div
                  className={`inline-flex items-center justify-center w-3 h-3 ${markerColor} rounded-full ml-1.5`}
                />
              )}
              {markerType === 'icon' && item.icon && (
                <div
                  className={`inline-flex items-center justify-center w-8 h-8 text-white ${markerColor} rounded-full`}
                >
                  {item.icon}
                </div>
              )}
            </div>

            {/* Content */}
            <div className={`flex flex-col flex-1 ${isLast ? 'pb-0' : 'pb-6'}`}>
              <div className="flex items-start justify-between px-4 gap-4">
                <div className="flex flex-col flex-1 min-w-0">
                  <div className="text-sm font-bold text-gray-900 dark:text-white">
                    {item.title}
                  </div>
                  {item.description && (
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {item.description}
                    </div>
                  )}
                  {item.timestamp && (
                    <div className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                      {item.timestamp}
                    </div>
                  )}
                </div>
                {item.status && (
                  <div className="shrink-0">
                    {item.status}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

Timeline.displayName = 'Timeline';

export default Timeline;
