"use client";

import React from 'react';
import { Avatar } from '../atoms/Avatar';
import { Badge } from '../atoms/Badge';

export interface ListItemProps {
  /** Main title/label */
  title: string;
  /** Optional subtitle or description */
  subtitle?: string;
  /** Optional secondary text */
  description?: string;
  /** Optional avatar/image URL */
  avatar?: string;
  /** Optional avatar initials (if no image) */
  initials?: string;
  /** Optional right-side content */
  rightContent?: React.ReactNode;
  /** Optional badge */
  badge?: {
    label: string | number;
    variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info' | 'light';
  };
  /** Optional timestamp */
  timestamp?: string;
  /** Optional icon */
  icon?: React.ReactNode;
  /** Click handler */
  onClick?: () => void;
  /** Additional className */
  className?: string;
}

/**
 * ListItem Molecule Component
 * 
 * A flexible list item component for displaying content in list views.
 * Supports various layouts with avatars, badges, timestamps, and custom content.
 * 
 * Features:
 * - Dark mode support
 * - Avatar or initials display
 * - Optional badge and timestamp
 * - Flexible right-side content
 * - Click handling
 * - Multiple content layouts
 * 
 * @example
 * ```tsx
 * // Simple list item
 * <ListItem
 *   title="John Doe"
 *   subtitle="Software Engineer"
 * />
 * 
 * // With avatar and badge
 * <ListItem
 *   title="Jane Smith"
 *   subtitle="Sent you a message"
 *   avatar="/images/jane.jpg"
 *   badge={{ label: 3, variant: 'danger' }}
 *   timestamp="2 min ago"
 * />
 * 
 * // With initials and description
 * <ListItem
 *   title="Alice Brown"
 *   subtitle="Product Manager"
 *   description="Reviewed your pull request"
 *   initials="AB"
 *   timestamp="1 hour ago"
 * />
 * 
 * // With custom right content
 * <ListItem
 *   title="Project Alpha"
 *   subtitle="In Progress"
 *   rightContent={
 *     <ProgressBar value={75} className="w-24" />
 *   }
 * />
 * 
 * // Clickable with icon
 * <ListItem
 *   title="Notifications"
 *   subtitle="3 new alerts"
 *   icon={<FiBell />}
 *   badge={{ label: 3, variant: 'danger' }}
 *   onClick={() => navigate('/notifications')}
 * />
 * ```
 */
export const ListItem: React.FC<ListItemProps> = ({
  title,
  subtitle,
  description,
  avatar,
  initials,
  rightContent,
  badge,
  timestamp,
  icon,
  onClick,
  className = '',
}) => {
  const hasAvatar = avatar || initials;
  const hasMetadata = description || timestamp;

  return (
    <div
      className={`flex items-center justify-start p-2 space-x-4 transition-colors ${
        onClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg' : ''
      } ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
    >
      {/* Avatar/Icon/Initials */}
      {hasAvatar && (
        <div className="shrink-0 w-8">
          {avatar ? (
            <img
              src={avatar}
              alt={title}
              className="h-8 w-8 rounded-full shadow-lg ring-2 ring-white dark:ring-gray-900 object-cover"
            />
          ) : initials ? (
            <span className="flex items-center justify-center w-8 h-8 text-sm font-bold text-white bg-blue-500 rounded-full">
              {initials}
            </span>
          ) : null}
        </div>
      )}

      {icon && !hasAvatar && (
        <div className="shrink-0 w-5 h-5 text-gray-500 dark:text-gray-400">
          {icon}
        </div>
      )}

      {/* Content */}
      <div className="flex flex-col flex-1 min-w-0">
        <div className={`text-sm ${subtitle ? 'font-bold' : ''} truncate`}>
          {title}
        </div>
        {subtitle && (
          <div className="text-sm text-gray-600 dark:text-gray-400 truncate">
            {subtitle}
          </div>
        )}
        {hasMetadata && (
          <div className="flex items-center gap-2 mt-1">
            {description && (
              <div className="text-xs text-gray-500 dark:text-gray-500 truncate">
                {description}
              </div>
            )}
            {timestamp && (
              <div className="text-xs text-gray-500 dark:text-gray-500 whitespace-nowrap">
                {timestamp}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Content */}
      {(rightContent || badge || timestamp) && (
        <div className="flex items-center gap-2 shrink-0">
          {rightContent}
          {badge && (
            <Badge variant={badge.variant || 'primary'} size="sm">
              {badge.label}
            </Badge>
          )}
          {timestamp && !description && (
            <span className="text-xs text-gray-500 dark:text-gray-500 whitespace-nowrap">
              {timestamp}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

ListItem.displayName = 'ListItem';

export default ListItem;
