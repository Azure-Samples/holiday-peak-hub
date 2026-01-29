/**
 * SearchInput Molecule Component
 * Search input with icon and clear button
 * Extracted pattern from navbar/search.tsx
 */

import React, { useState, forwardRef } from 'react';
import { FiSearch, FiX } from 'react-icons/fi';
import { cn } from '../utils';
import type { Size, BaseComponentProps } from '../types';

export interface SearchInputProps extends BaseComponentProps {
  /** Input name */
  name?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Input value (controlled) */
  value?: string;
  /** Default value */
  defaultValue?: string;
  /** Change handler */
  onChange?: (value: string) => void;
  /** Submit handler (on Enter or search icon click) */
  onSearch?: (value: string) => void;
  /** Clear handler */
  onClear?: () => void;
  /** Input size */
  size?: Size;
  /** Whether input is disabled */
  disabled?: boolean;
  /** Whether to show clear button */
  showClearButton?: boolean;
  /** Whether to auto-focus on mount */
  autoFocus?: boolean;
  /** Debounce delay in ms */
  debounceMs?: number;
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  (
    {
      name = 'search',
      placeholder = 'Search...',
      value: controlledValue,
      defaultValue = '',
      onChange,
      onSearch,
      onClear,
      size = 'md',
      disabled = false,
      showClearButton = true,
      autoFocus = false,
      debounceMs = 0,
      className,
      testId,
      ariaLabel,
    },
    ref
  ) => {
    const [internalValue, setInternalValue] = useState(defaultValue);
    const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

    const isControlled = controlledValue !== undefined;
    const value = isControlled ? controlledValue : internalValue;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value;

      if (!isControlled) {
        setInternalValue(newValue);
      }

      if (onChange) {
        if (debounceMs > 0) {
          if (debounceTimer) clearTimeout(debounceTimer);
          setDebounceTimer(
            setTimeout(() => onChange(newValue), debounceMs)
          );
        } else {
          onChange(newValue);
        }
      }
    };

    const handleSearch = () => {
      if (onSearch) {
        onSearch(value);
      }
    };

    const handleClear = () => {
      if (!isControlled) {
        setInternalValue('');
      }
      onChange?.('');
      onClear?.();
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        handleSearch();
      }
    };

    const sizeClasses = {
      xs: 'h-8 pl-8 pr-8 text-xs',
      sm: 'h-9 pl-9 pr-9 text-sm',
      md: 'h-10 pl-10 pr-10 text-sm',
      lg: 'h-11 pl-11 pr-11 text-base',
      xl: 'h-12 pl-12 pr-12 text-lg',
    };

    const iconSizes = {
      xs: 'w-3 h-3',
      sm: 'w-4 h-4',
      md: 'w-4 h-4',
      lg: 'w-5 h-5',
      xl: 'w-6 h-6',
    };

    return (
      <div
        data-testid={testId}
        className={cn('relative inline-flex items-center', className)}
      >
        {/* Search Icon */}
        <div className="absolute left-3 pointer-events-none">
          <FiSearch
            className={cn(
              'text-gray-400 dark:text-gray-500',
              iconSizes[size]
            )}
          />
        </div>

        {/* Input */}
        <input
          ref={ref}
          type="search"
          name={name}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          autoFocus={autoFocus}
          aria-label={ariaLabel || placeholder}
          className={cn(
            'w-full',
            'border border-gray-300 dark:border-gray-700',
            'bg-white dark:bg-gray-800',
            'text-gray-900 dark:text-white',
            'placeholder-gray-400 dark:placeholder-gray-500',
            'rounded-lg',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'transition-colors duration-200',
            disabled && 'opacity-50 cursor-not-allowed',
            sizeClasses[size]
          )}
        />

        {/* Clear Button */}
        {showClearButton && value && (
          <button
            type="button"
            onClick={handleClear}
            disabled={disabled}
            className={cn(
              'absolute right-3',
              'text-gray-400 hover:text-gray-600',
              'dark:text-gray-500 dark:hover:text-gray-400',
              'transition-colors duration-200',
              'focus:outline-none'
            )}
            aria-label="Clear search"
          >
            <FiX className={iconSizes[size]} />
          </button>
        )}
      </div>
    );
  }
);

SearchInput.displayName = 'SearchInput';
