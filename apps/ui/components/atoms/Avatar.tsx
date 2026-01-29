/**
 * Avatar Atom Component
 * User avatar with image and fallback initials
 */

import React, { useState } from 'react';
import { cn } from '../utils';
import type { Size, BaseComponentProps } from '../types';

export interface AvatarProps extends BaseComponentProps {
  /** Avatar image URL */
  src?: string;
  /** Alt text for image */
  alt?: string;
  /** User name (for initials fallback) */
  name?: string;
  /** Avatar size */
  size?: Size;
  /** Whether avatar is circular */
  rounded?: boolean;
  /** Custom initials (overrides name) */
  initials?: string;
  /** Background color for initials */
  bgColor?: string;
  /** Text color for initials */
  textColor?: string;
  /** Status indicator */
  status?: 'online' | 'offline' | 'away' | 'busy' | null;
}

const sizeMap: Record<Size, { container: string; text: string; status: string }> = {
  xs: { container: 'h-6 w-6', text: 'text-xs', status: 'h-1.5 w-1.5' },
  sm: { container: 'h-8 w-8', text: 'text-sm', status: 'h-2 w-2' },
  md: { container: 'h-10 w-10', text: 'text-base', status: 'h-2.5 w-2.5' },
  lg: { container: 'h-12 w-12', text: 'text-lg', status: 'h-3 w-3' },
  xl: { container: 'h-16 w-16', text: 'text-xl', status: 'h-4 w-4' },
};

const statusColors = {
  online: 'bg-green-500',
  offline: 'bg-gray-400',
  away: 'bg-yellow-500',
  busy: 'bg-red-500',
};

const getInitials = (name: string): string => {
  const parts = name.trim().split(' ');
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
};

export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt,
  name,
  size = 'md',
  rounded = true,
  initials,
  bgColor = 'bg-blue-500',
  textColor = 'text-white',
  status,
  className,
  testId,
  ariaLabel,
}) => {
  const [imageError, setImageError] = useState(false);
  
  const displayInitials = initials || (name ? getInitials(name) : '??');
  const showInitials = !src || imageError;
  
  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || alt || name}
      className={cn(
        'relative inline-flex items-center justify-center',
        'overflow-hidden',
        sizeMap[size].container,
        rounded ? 'rounded-full' : 'rounded-md',
        showInitials && bgColor,
        className
      )}
    >
      {src && !imageError ? (
        <img
          src={src}
          alt={alt || name || 'Avatar'}
          onError={() => setImageError(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        <span
          className={cn(
            'font-semibold select-none',
            sizeMap[size].text,
            textColor
          )}
        >
          {displayInitials}
        </span>
      )}
      
      {status && (
        <span
          aria-label={`Status: ${status}`}
          className={cn(
            'absolute bottom-0 right-0',
            'rounded-full border-2 border-white dark:border-gray-800',
            sizeMap[size].status,
            statusColors[status]
          )}
        />
      )}
    </div>
  );
};

Avatar.displayName = 'Avatar';
