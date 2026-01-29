/**
 * Button Atom Component
 * A highly configurable button component with variants, sizes, and states
 */

import React from 'react';
import { cn, sizeClasses, variantClasses } from '../utils';
import type { Size, Variant, InteractiveProps } from '../types';

export interface ButtonProps extends InteractiveProps {
  /** Button content */
  children: React.ReactNode;
  /** Button variant style */
  variant?: Variant;
  /** Button size */
  size?: Size;
  /** Icon to display before text */
  iconLeft?: React.ReactNode;
  /** Icon to display after text */
  iconRight?: React.ReactNode;
  /** Whether button takes full width */
  fullWidth?: boolean;
  /** Button HTML type */
  type?: 'button' | 'submit' | 'reset';
  /** Whether button shows loading spinner */
  loading?: boolean;
  /** Whether to show only icon (no padding for text) */
  iconOnly?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  iconLeft,
  iconRight,
  fullWidth = false,
  type = 'button',
  disabled = false,
  loading = false,
  iconOnly = false,
  className,
  onClick,
  testId,
  ariaLabel,
  ...props
}) => {
  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      disabled={isDisabled}
      onClick={onClick}
      data-testid={testId}
      aria-label={ariaLabel}
      aria-disabled={isDisabled}
      className={cn(
        // Base styles
        'inline-flex items-center justify-center font-bold uppercase',
        'transition-colors duration-200',
        'focus:outline-none focus:ring-2 focus:ring-offset-2',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'rounded-lg',
        
        // Size variants
        !iconOnly && sizeClasses.button[size],
        iconOnly && (size === 'xs' ? 'p-1' : size === 'sm' ? 'p-1.5' : size === 'md' ? 'p-2' : size === 'lg' ? 'p-2.5' : 'p-3'),
        
        // Variant styles
        variantClasses.button[variant],
        
        // Full width
        fullWidth && 'w-full',
        
        // Custom classes
        className
      )}
      {...props}
    >
      {loading && (
        <svg
          className={cn(
            'animate-spin',
            !iconOnly && children && 'mr-2',
            size === 'xs' ? 'h-3 w-3' : size === 'sm' ? 'h-4 w-4' : 'h-5 w-5'
          )}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      
      {!loading && iconLeft && (
        <span className={cn(!iconOnly && children && 'mr-2')}>
          {iconLeft}
        </span>
      )}
      
      {!iconOnly && children}
      
      {!loading && iconRight && (
        <span className={cn(!iconOnly && children && 'ml-2')}>
          {iconRight}
        </span>
      )}
    </button>
  );
};

Button.displayName = 'Button';
