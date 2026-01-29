/**
 * Badge Atom Component
 * Small status indicators and labels
 * Migrated from components/badges/index.tsx with enhancements
 */

import React from 'react';
import { cn, sizeClasses, variantClasses, roundedClasses } from '../utils';
import type { Size, Variant, Rounded, BaseComponentProps } from '../types';

export interface BadgeProps extends BaseComponentProps {
  /** Badge content */
  children: React.ReactNode;
  /** Badge variant style */
  variant?: Variant;
  /** Badge size */
  size?: Size;
  /** Border radius */
  rounded?: Rounded;
  /** Whether badge has outline style */
  outlined?: boolean;
  /** Whether badge is circular (dot indicator) */
  dot?: boolean;
  /** Icon to show before text */
  icon?: React.ReactNode;
  /** Whether to remove padding (for icon-only badges) */
  noPadding?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  rounded = 'md',
  outlined = false,
  dot = false,
  icon,
  noPadding = false,
  className,
  testId,
  ariaLabel,
}) => {
  if (dot) {
    return (
      <span
        data-testid={testId}
        aria-label={ariaLabel}
        className={cn(
          'inline-flex items-center justify-center',
          'rounded-full',
          'uppercase font-bold',
          'leading-none',
          
          // Size variants for dot
          size === 'xs' && 'h-4 w-4 text-xs',
          size === 'sm' && 'h-5 w-5 text-xs',
          size === 'md' && 'h-6 w-6 text-xs',
          size === 'lg' && 'h-7 w-7 text-sm',
          size === 'xl' && 'h-8 w-8 text-sm',
          
          // Variant styles
          outlined
            ? `bg-transparent border-2 border-current ${variantClasses.badge[variant]}`
            : variantClasses.badge[variant],
          
          className
        )}
      >
        {children}
      </span>
    );
  }

  return (
    <span
      data-testid={testId}
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center justify-center',
        'uppercase font-bold',
        'text-center',
        
        // Size variants
        !noPadding && sizeClasses.badge[size],
        
        // Rounded variants
        roundedClasses[rounded],
        
        // Variant styles
        outlined
          ? `bg-transparent border border-current ${variantClasses.badge[variant]}`
          : variantClasses.badge[variant],
        
        className
      )}
    >
      {icon && <span className={cn(children && 'mr-1')}>{icon}</span>}
      {children}
    </span>
  );
};

Badge.displayName = 'Badge';
