"use client";

import React from 'react';
import { Button } from '../atoms/Button';

export interface ProfileCardProps {
  /** User name */
  name: string;
  /** User avatar/profile image URL */
  avatar: string;
  /** Cover/background image URL */
  coverImage?: string;
  /** User title or role */
  title?: string;
  /** Statistics or metadata */
  stats?: Array<{
    label: string;
    value: string | number;
  }>;
  /** Action buttons */
  actions?: Array<{
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'outline';
  }>;
  /** Additional className */
  className?: string;
}

/**
 * ProfileCard Molecule Component
 * 
 * A user profile card with cover image, avatar, and action buttons.
 * Perfect for user profiles, member cards, and social features.
 * 
 * Features:
 * - Dark mode support
 * - Cover image with avatar overlay
 * - Optional statistics display
 * - Customizable action buttons
 * - Responsive design
 * 
 * @example
 * ```tsx
 * // Basic profile card
 * <ProfileCard
 *   name="John Doe"
 *   avatar="/images/john.jpg"
 *   coverImage="/images/cover.jpg"
 *   title="Software Engineer"
 *   actions={[
 *     { label: 'Follow', onClick: () => follow(), variant: 'primary' },
 *     { label: 'Message', onClick: () => message(), variant: 'secondary' },
 *   ]}
 * />
 * 
 * // With statistics
 * <ProfileCard
 *   name="Jane Smith"
 *   avatar="/images/jane.jpg"
 *   coverImage="/images/cover2.jpg"
 *   title="Product Manager"
 *   stats={[
 *     { label: 'Followers', value: '1.2K' },
 *     { label: 'Following', value: '345' },
 *     { label: 'Posts', value: '89' },
 *   ]}
 *   actions={[
 *     { label: 'Subscribe', onClick: () => subscribe() },
 *     { label: 'Follow', onClick: () => follow() },
 *   ]}
 * />
 * 
 * // Minimal version
 * <ProfileCard
 *   name="Alice Brown"
 *   avatar="/images/alice.jpg"
 *   title="Designer"
 * />
 * ```
 */
export const ProfileCard: React.FC<ProfileCardProps> = ({
  name,
  avatar,
  coverImage,
  title,
  stats,
  actions,
  className = '',
}) => {
  return (
    <div
      className={`relative flex flex-col w-full overflow-hidden bg-white dark:bg-gray-900 rounded-lg shadow-lg ${className}`}
    >
      {/* Cover Image */}
      {coverImage ? (
        <div className="relative h-48 w-full overflow-hidden">
          <img
            src={coverImage}
            alt={`${name} cover`}
            className="w-full h-full object-cover"
          />
        </div>
      ) : (
        <div className="h-48 w-full bg-gradient-to-br from-blue-500 to-purple-600" />
      )}

      {/* Profile Content */}
      <div className="relative px-6 pb-6">
        {/* Avatar - Overlapping cover */}
        <div className="flex items-start -mt-12 mb-4">
          <img
            src={avatar}
            alt={name}
            className="w-24 h-24 rounded-full shadow-xl ring-4 ring-white dark:ring-gray-900 object-cover"
          />
        </div>

        {/* User Info */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex-1">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              {name}
            </h3>
            {title && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {title}
              </p>
            )}

            {/* Stats */}
            {stats && stats.length > 0 && (
              <div className="flex items-center gap-6 mt-4">
                {stats.map((stat, index) => (
                  <div key={index} className="flex flex-col">
                    <span className="text-lg font-bold text-gray-900 dark:text-white">
                      {stat.value}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">
                      {stat.label}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          {actions && actions.length > 0 && (
            <div className="flex items-center gap-2 shrink-0">
              {actions.map((action, index) => (
                <Button
                  key={index}
                  variant={action.variant || 'primary'}
                  size="sm"
                  onClick={action.onClick}
                >
                  {action.label}
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

ProfileCard.displayName = 'ProfileCard';

export default ProfileCard;
