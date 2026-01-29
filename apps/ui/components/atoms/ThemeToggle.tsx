'use client';

import React from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { FiSun, FiMoon } from 'react-icons/fi';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface ThemeToggleProps extends BaseComponentProps {
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show text label */
  showLabel?: boolean;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  size = 'md',
  showLabel = false,
  className,
  testId,
  ariaLabel,
}) => {
  const { theme, toggleTheme } = useTheme();

  const sizeClasses = {
    sm: 'p-1.5',
    md: 'p-2',
    lg: 'p-3',
  };

  const iconSizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  return (
    <button
      data-testid={testId}
      aria-label={ariaLabel || 'Toggle theme'}
      onClick={toggleTheme}
      className={cn(
        'inline-flex items-center justify-center rounded-lg',
        'text-gray-700 dark:text-gray-300',
        'hover:bg-gray-100 dark:hover:bg-gray-800',
        'focus:outline-none focus:ring-2 focus:ring-ocean-500 dark:focus:ring-ocean-300',
        'transition-colors duration-200',
        sizeClasses[size],
        className
      )}
    >
      {theme === 'light' ? (
        <FiMoon className={iconSizeClasses[size]} />
      ) : (
        <FiSun className={iconSizeClasses[size]} />
      )}
      {showLabel && (
        <span className="ml-2 text-sm font-medium">
          {theme === 'light' ? 'Dark' : 'Light'}
        </span>
      )}
    </button>
  );
};

ThemeToggle.displayName = 'ThemeToggle';
