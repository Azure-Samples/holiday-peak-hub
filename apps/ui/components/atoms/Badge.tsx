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
  variant?: Variant | 'glass';
  /** Badge size */
  size?: Size;
  /** Border radius */
  rounded?: Rounded | 'full';
  /** Whether badge has outline style */
  outlined?: boolean;
  /** Whether badge is circular (dot indicator) */
  dot?: boolean;
  /** Icon to show before text */
  icon?: React.ReactNode;
  /** Whether to remove padding (for icon-only badges) */
  noPadding?: boolean;
  /** Enable hover animation */
  animated?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  rounded = 'full',
  outlined = false,
  dot = false,
  icon,
  noPadding = false,
  animated = true,
  className,
  testId,
  ariaLabel,
}) => {
  const isGlass = variant === 'glass';

  if (dot) {
    return (
      <span
        data-testid={testId}
        aria-label={ariaLabel}
        className={cn(
          'relative inline-flex items-center justify-center',
          'rounded-full',
        'font-semibold tracking-wide',
        'leading-none',
        animated && 'transition-all duration-500 ease-[cubic-bezier(0.25,1,0.5,1)] hover:scale-110',
          size === 'sm' && 'h-4 w-4 text-xs',
          size === 'md' && 'h-5 w-5 text-xs',
          size === 'lg' && 'h-6 w-6 text-sm',
          size === 'xl' && 'h-8 w-8 text-base',
          
          // Variant styles
          outlined || isGlass
            ? `bg-transparent border-2 border-current ${isGlass ? 'backdrop-blur-md bg-white/10 dark:bg-black/10' : ''} ${variant !== 'glass' ? variantClasses.badge[variant] : 'text-gray-900 dark:text-white border-white/30'}`
            : variantClasses.badge[variant as Variant],
          
          className
        )}
      >
        {/* Animated pulse shadow effect for dots */}
        {animated && (
          <span className={cn(
            'absolute inset-0 rounded-full animate-ping opacity-25',
            outlined ? 'bg-current' : 'bg-white/50'
          )} />
        )}
        {children}
      </span>
    );
  }

  return (
    <span
      data-testid={testId}
      aria-label={ariaLabel}
      className={cn(
        'group relative inline-flex items-center justify-center overflow-hidden',
        'font-semibold tracking-wide',
        'text-center whitespace-nowrap',
        
        // Refined interaction styles
        animated && 'transition-all duration-400 ease-[cubic-bezier(0.25,1,0.5,1)] hover:shadow-sm cursor-default',
        
        // Size variants
        !noPadding && sizeClasses.badge[size],
        
        // Rounded variants
        rounded === 'full' ? 'rounded-full' : roundedClasses[rounded],
        
        // Variant styles
        outlined || isGlass
          ? `bg-transparent border ${isGlass ? 'backdrop-blur-md bg-white/20 dark:bg-black/20 text-gray-800 dark:text-gray-100 border-white/40 dark:border-white/20 shadow-[0_4px_12px_rgba(0,0,0,0.05)]' : `border-current ${variantClasses.badge[variant as Variant]}`}`
          : variantClasses.badge[variant as Variant],
        
        className
      )}
    >
      {/* SVG Micro-interaction glow */}
      {animated && (
         <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-[150%] skew-x-[-30deg] transition-transform duration-[1.5s] ease-[cubic-bezier(0.25,1,0.5,1)] group-hover:translate-x-[150%]" />
      )}
      
      <span className="relative z-10 flex items-center gap-1.5">
        {icon && (
          <span className="transition-transform duration-300 group-hover:scale-110 group-hover:rotate-6">
            {icon}
          </span>
        )}
        {children}
      </span>
    </span>
  );
};

Badge.displayName = 'Badge';
