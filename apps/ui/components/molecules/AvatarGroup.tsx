"use client";

import React from 'react';
import { Avatar } from '../atoms/Avatar';

export interface AvatarGroupProps {
  /** Array of avatar image URLs */
  avatars: string[];
  /** Maximum number of avatars to display */
  max?: number;
  /** Size of avatars */
  size?: 'sm' | 'md' | 'lg';
  /** Show count of remaining avatars */
  showRemaining?: boolean;
  /** Additional className for container */
  className?: string;
}

const sizeClasses = {
  sm: 'h-6 w-6 text-xs',
  md: 'h-8 w-8 text-sm',
  lg: 'h-10 w-10 text-base',
};

/**
 * AvatarGroup Molecule Component
 * 
 * Displays a group of avatars in an overlapping horizontal stack.
 * Commonly used to show team members, participants, or collaborators.
 * 
 * Features:
 * - Dark mode support with ring styling
 * - Configurable size (sm, md, lg)
 * - Maximum display limit with overflow counter
 * - Overlapping visual style
 * - Responsive and accessible
 * 
 * @example
 * ```tsx
 * // Basic avatar group
 * <AvatarGroup
 *   avatars={[
 *     '/images/user1.jpg',
 *     '/images/user2.jpg',
 *     '/images/user3.jpg',
 *   ]}
 * />
 * 
 * // Limited display with counter
 * <AvatarGroup
 *   avatars={teamMembers.map(m => m.avatarUrl)}
 *   max={4}
 *   showRemaining
 *   size="lg"
 * />
 * 
 * // Small size for compact spaces
 * <AvatarGroup
 *   avatars={participants}
 *   size="sm"
 *   max={3}
 * />
 * ```
 */
export const AvatarGroup: React.FC<AvatarGroupProps> = ({
  avatars,
  max = avatars.length,
  size = 'md',
  showRemaining = true,
  className = '',
}) => {
  const displayAvatars = avatars.slice(0, max);
  const remaining = avatars.length - max;

  return (
    <div className={`flex flex-row items-center justify-start ${className}`}>
      {displayAvatars.map((avatarUrl, index) => (
        <img
          key={index}
          src={avatarUrl}
          alt={`Avatar ${index + 1}`}
          className={`${sizeClasses[size]} ring-2 ring-white dark:ring-gray-900 rounded-full ${
            index > 0 ? '-ml-3' : ''
          } object-cover`}
        />
      ))}
      {showRemaining && remaining > 0 && (
        <div
          className={`${sizeClasses[size]} ring-2 ring-white dark:ring-gray-900 rounded-full -ml-3 bg-gray-200 dark:bg-gray-700 flex items-center justify-center font-semibold text-gray-700 dark:text-gray-300`}
        >
          +{remaining}
        </div>
      )}
    </div>
  );
};

AvatarGroup.displayName = 'AvatarGroup';

export default AvatarGroup;
