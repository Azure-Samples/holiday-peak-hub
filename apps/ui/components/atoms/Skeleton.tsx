/**
 * Skeleton Atom Component
 * Loading placeholder with pulse animation
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface SkeletonProps extends BaseComponentProps {
  /** Skeleton variant */
  variant?: 'text' | 'circular' | 'rectangular';
  /** Width (CSS value or 'full') */
  width?: string | number;
  /** Height (CSS value) */
  height?: string | number;
  /** Whether to animate */
  animate?: boolean;
  /** Number of text lines (for text variant) */
  lines?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'rectangular',
  width,
  height,
  animate = true,
  lines = 1,
  className,
  testId,
  ariaLabel,
}) => {
  const baseStyles = cn(
    'bg-gray-200 dark:bg-gray-700',
    animate && 'animate-pulse'
  );

  const getWidthClass = () => {
    if (!width) return 'w-full';
    if (width === 'full') return 'w-full';
    if (typeof width === 'number') return '';
    return width;
  };

  const getHeightClass = () => {
    if (!height) {
      if (variant === 'text') return 'h-4';
      if (variant === 'circular') return 'h-12';
      return 'h-24';
    }
    if (typeof height === 'number') return '';
    return height;
  };

  const inlineStyles: React.CSSProperties = {
    ...(typeof width === 'number' && { width: `${width}px` }),
    ...(typeof height === 'number' && { height: `${height}px` }),
  };

  if (variant === 'circular') {
    return (
      <div
        data-testid={testId}
        aria-label={ariaLabel || 'Loading...'}
        role="status"
        style={inlineStyles}
        className={cn(
          baseStyles,
          'rounded-full',
          getWidthClass(),
          getHeightClass(),
          className
        )}
      />
    );
  }

  if (variant === 'text' && lines > 1) {
    return (
      <div
        data-testid={testId}
        aria-label={ariaLabel || 'Loading...'}
        role="status"
        className={cn('space-y-2', className)}
      >
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            style={inlineStyles}
            className={cn(
              baseStyles,
              'rounded',
              getWidthClass(),
              'h-4',
              index === lines - 1 && 'w-3/4' // Last line shorter
            )}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Loading...'}
      role="status"
      style={inlineStyles}
      className={cn(
        baseStyles,
        variant === 'text' ? 'rounded' : 'rounded-md',
        getWidthClass(),
        getHeightClass(),
        className
      )}
    />
  );
};

Skeleton.displayName = 'Skeleton';
