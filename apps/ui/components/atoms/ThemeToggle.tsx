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
        'inline-flex items-center justify-center rounded-full',
        'text-gray-500 dark:text-gray-400',
        'hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-900 dark:focus-visible:ring-white',
        'transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)]',
        'active:scale-90',
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
