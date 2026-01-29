/**
 * Select Atom Component
 * Dropdown select input with react-hook-form support
 */

import React, { forwardRef } from 'react';
import { useFormContext } from 'react-hook-form';
import { cn, sizeClasses } from '../utils';
import type { Size, FormFieldBaseProps } from '../types';

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends Omit<FormFieldBaseProps, 'label' | 'hint'> {
  /** Select options */
  options: SelectOption[];
  /** Select size */
  size?: Size;
  /** Default value */
  defaultValue?: string | number;
  /** Current value (controlled) */
  value?: string | number;
  /** Change handler */
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  /** Blur handler */
  onBlur?: (e: React.FocusEvent<HTMLSelectElement>) => void;
  /** Whether to use react-hook-form integration */
  useRHF?: boolean;
  /** Validation rules for react-hook-form */
  rules?: any;
  /** Whether to allow multiple selections */
  multiple?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      name,
      options,
      size = 'md',
      placeholder = 'Select an option',
      defaultValue,
      value,
      onChange,
      onBlur,
      disabled = false,
      required = false,
      error,
      useRHF = false,
      rules,
      multiple = false,
      className,
      testId,
      ariaLabel,
      ...props
    },
    ref
  ) => {
    // React Hook Form integration
    const formContext = useRHF ? useFormContext() : null;
    const registration = formContext && name ? formContext.register(name, rules) : null;

    const hasError = error || (formContext?.formState.errors[name] && true);

    return (
      <select
        ref={registration ? registration.ref : ref}
        name={name}
        defaultValue={defaultValue}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        disabled={disabled}
        required={required}
        multiple={multiple}
        data-testid={testId}
        aria-label={ariaLabel}
        aria-invalid={hasError}
        aria-required={required}
        className={cn(
          // Base styles
          'block w-full',
          'border rounded-md',
          'bg-white dark:bg-gray-800',
          'text-gray-900 dark:text-white',
          'transition-colors duration-200',
          
          // Border and focus states
          hasError
            ? 'border-red-300 dark:border-red-700 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 dark:border-gray-700 focus:border-blue-500 focus:ring-blue-500',
          
          'focus:outline-none focus:ring-1',
          
          // Disabled state
          disabled && 'opacity-50 cursor-not-allowed bg-gray-50 dark:bg-gray-900',
          
          // Size variants
          sizeClasses.input[size],
          
          // Custom classes
          className
        )}
        {...(registration ? { ...registration, ref: registration.ref } : {})}
        {...props}
      >
        {placeholder && !multiple && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
            disabled={option.disabled}
          >
            {option.label}
          </option>
        ))}
      </select>
    );
  }
);

Select.displayName = 'Select';
