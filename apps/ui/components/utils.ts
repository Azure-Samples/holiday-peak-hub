/**
 * Utility Functions for Atomic Components
 * Provides helper functions for styling, formatting, and common operations
 */

import clsx from 'clsx';
import type { Size, Variant, ColorScheme, Rounded, Spacing } from '../types';

// ===== CLASS NAME UTILITIES =====

/**
 * Merges multiple class names, filtering out falsy values
 */
export const cn = (...classes: (string | undefined | null | boolean)[]): string => {
  return clsx(classes);
};

// ===== SIZE UTILITIES =====

export const sizeClasses = {
  button: {
    xs: 'px-2 py-1 text-xs',
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-base',
    xl: 'px-6 py-3 text-lg',
  },
  input: {
    xs: 'px-2 py-1 text-xs',
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-3 py-2 text-sm',
    lg: 'px-4 py-2.5 text-base',
    xl: 'px-5 py-3 text-lg',
  },
  text: {
    xs: 'text-xs',
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl',
  },
  icon: {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
    xl: 'w-8 h-8',
  },
  badge: {
    xs: 'px-1.5 py-0.5 text-xs',
    sm: 'px-2 py-1 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-sm',
    xl: 'px-4 py-2 text-base',
  },
};

// ===== VARIANT UTILITIES =====

export const variantClasses = {
  button: {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500',
    success: 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500',
    warning: 'bg-yellow-500 text-white hover:bg-yellow-600 focus:ring-yellow-500',
    error: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    info: 'bg-blue-500 text-white hover:bg-blue-600 focus:ring-blue-400',
    ghost: 'bg-transparent text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800',
  },
  badge: {
    primary: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    secondary: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
    error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    info: 'bg-blue-50 text-blue-700 dark:bg-blue-800 dark:text-blue-200',
    ghost: 'bg-transparent text-gray-700 dark:text-gray-300',
  },
  alert: {
    primary: 'bg-blue-50 text-blue-900 border-blue-200 dark:bg-blue-900 dark:text-blue-100',
    secondary: 'bg-gray-50 text-gray-900 border-gray-200 dark:bg-gray-800 dark:text-gray-100',
    success: 'bg-green-50 text-green-900 border-green-200 dark:bg-green-900 dark:text-green-100',
    warning: 'bg-yellow-50 text-yellow-900 border-yellow-200 dark:bg-yellow-900 dark:text-yellow-100',
    error: 'bg-red-50 text-red-900 border-red-200 dark:bg-red-900 dark:text-red-100',
    info: 'bg-blue-50 text-blue-900 border-blue-200 dark:bg-blue-800 dark:text-blue-100',
    ghost: 'bg-transparent text-gray-900 dark:text-gray-100',
  },
};

// ===== COLOR UTILITIES =====

export const colorClasses = {
  text: {
    blue: 'text-blue-600 dark:text-blue-400',
    green: 'text-green-600 dark:text-green-400',
    red: 'text-red-600 dark:text-red-400',
    yellow: 'text-yellow-600 dark:text-yellow-400',
    gray: 'text-gray-600 dark:text-gray-400',
    purple: 'text-purple-600 dark:text-purple-400',
    pink: 'text-pink-600 dark:text-pink-400',
    indigo: 'text-indigo-600 dark:text-indigo-400',
  },
  bg: {
    blue: 'bg-blue-600 dark:bg-blue-700',
    green: 'bg-green-600 dark:bg-green-700',
    red: 'bg-red-600 dark:bg-red-700',
    yellow: 'bg-yellow-500 dark:bg-yellow-600',
    gray: 'bg-gray-600 dark:bg-gray-700',
    purple: 'bg-purple-600 dark:bg-purple-700',
    pink: 'bg-pink-600 dark:bg-pink-700',
    indigo: 'bg-indigo-600 dark:bg-indigo-700',
  },
  border: {
    blue: 'border-blue-600 dark:border-blue-400',
    green: 'border-green-600 dark:border-green-400',
    red: 'border-red-600 dark:border-red-400',
    yellow: 'border-yellow-500 dark:border-yellow-400',
    gray: 'border-gray-300 dark:border-gray-600',
    purple: 'border-purple-600 dark:border-purple-400',
    pink: 'border-pink-600 dark:border-pink-400',
    indigo: 'border-indigo-600 dark:border-indigo-400',
  },
};

// ===== ROUNDED UTILITIES =====

export const roundedClasses: Record<Rounded, string> = {
  none: 'rounded-none',
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
};

// ===== SPACING UTILITIES =====

export const spacingClasses: Record<Spacing, string> = {
  none: 'space-y-0',
  xs: 'space-y-1',
  sm: 'space-y-2',
  md: 'space-y-4',
  lg: 'space-y-6',
  xl: 'space-y-8',
};

// ===== FORMATTING UTILITIES =====

/**
 * Format currency with proper symbol and decimal places
 */
export const formatCurrency = (
  amount: number,
  currency: string = 'USD',
  locale: string = 'en-US'
): string => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
  }).format(amount);
};

/**
 * Format number with thousand separators
 */
export const formatNumber = (num: number, decimals: number = 0): string => {
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

/**
 * Format percentage
 */
export const formatPercent = (value: number, decimals: number = 0): string => {
  return `${value.toFixed(decimals)}%`;
};

/**
 * Calculate savings percentage
 */
export const calculateSavingsPercent = (msrp: number, salePrice: number): number => {
  if (msrp <= 0 || salePrice >= msrp) return 0;
  return Math.round(((msrp - salePrice) / msrp) * 100);
};

// ===== DATE/TIME UTILITIES =====

/**
 * Format date using date-fns
 */
export const formatDate = (date: string | Date, formatStr: string = 'MMM dd, yyyy'): string => {
  // This will use date-fns when implemented
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return dateObj.toLocaleDateString('en-US');
};

/**
 * Format relative time (e.g., "2 hours ago")
 */
export const formatRelativeTime = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - dateObj.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 30) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  return formatDate(dateObj);
};

// ===== VALIDATION UTILITIES =====

/**
 * Validate email format
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Validate phone number (basic US format)
 */
export const isValidPhone = (phone: string): boolean => {
  const phoneRegex = /^[\d\s\-()]+$/;
  return phoneRegex.test(phone) && phone.replace(/\D/g, '').length === 10;
};

/**
 * Validate zip code (US format)
 */
export const isValidZipCode = (zip: string): boolean => {
  const zipRegex = /^\d{5}(-\d{4})?$/;
  return zipRegex.test(zip);
};

// ===== STRING UTILITIES =====

/**
 * Truncate text with ellipsis
 */
export const truncate = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
};

/**
 * Capitalize first letter
 */
export const capitalize = (text: string): string => {
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
};

/**
 * Convert to title case
 */
export const toTitleCase = (text: string): string => {
  return text
    .split(' ')
    .map(word => capitalize(word))
    .join(' ');
};

// ===== ARRAY UTILITIES =====

/**
 * Group array items by key
 */
export const groupBy = <T>(array: T[], key: keyof T): Record<string, T[]> => {
  return array.reduce((acc, item) => {
    const groupKey = String(item[key]);
    if (!acc[groupKey]) acc[groupKey] = [];
    acc[groupKey].push(item);
    return acc;
  }, {} as Record<string, T[]>);
};

/**
 * Generate unique ID
 */
export const generateId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// ===== ACCESSIBILITY UTILITIES =====

/**
 * Generate ARIA attributes for interactive elements
 */
export const getAriaProps = (options: {
  label?: string;
  description?: string;
  expanded?: boolean;
  selected?: boolean;
  disabled?: boolean;
}) => {
  const props: Record<string, any> = {};
  
  if (options.label) props['aria-label'] = options.label;
  if (options.description) props['aria-describedby'] = options.description;
  if (options.expanded !== undefined) props['aria-expanded'] = options.expanded;
  if (options.selected !== undefined) props['aria-selected'] = options.selected;
  if (options.disabled) props['aria-disabled'] = true;
  
  return props;
};
