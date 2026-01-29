/**
 * Textarea Atom Component
 * Multi-line text input with react-hook-form support
 */

import React, { forwardRef } from 'react';
import { useFormContext } from 'react-hook-form';
import { cn } from '../utils';
import type { Size, FormFieldBaseProps } from '../types';

export interface TextareaProps extends Omit<FormFieldBaseProps, 'label' | 'hint'> {
  /** Textarea size (affects padding) */
  size?: Size;
  /** Number of visible text rows */
  rows?: number;
  /** Default value */
  defaultValue?: string;
  /** Current value (controlled) */
  value?: string;
  /** Change handler */
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  /** Blur handler */
  onBlur?: (e: React.FocusEvent<HTMLTextAreaElement>) => void;
  /** Whether to use react-hook-form integration */
  useRHF?: boolean;
  /** Validation rules for react-hook-form */
  rules?: any;
  /** Max length */
  maxLength?: number;
  /** Whether textarea is read-only */
  readOnly?: boolean;
  /** Resize behavior */
  resize?: 'none' | 'both' | 'horizontal' | 'vertical';
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      name,
      size = 'md',
      rows = 4,
      placeholder,
      defaultValue,
      value,
      onChange,
      onBlur,
      disabled = false,
      required = false,
      error,
      useRHF = false,
      rules,
      maxLength,
      readOnly = false,
      resize = 'vertical',
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

    const resizeClasses = {
      none: 'resize-none',
      both: 'resize',
      horizontal: 'resize-x',
      vertical: 'resize-y',
    };

    return (
      <textarea
        ref={registration ? registration.ref : ref}
        name={name}
        rows={rows}
        placeholder={placeholder}
        defaultValue={defaultValue}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        disabled={disabled}
        required={required}
        maxLength={maxLength}
        readOnly={readOnly}
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
          'placeholder-gray-400 dark:placeholder-gray-500',
          'transition-colors duration-200',
          
          // Border and focus states
          hasError
            ? 'border-red-300 dark:border-red-700 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 dark:border-gray-700 focus:border-blue-500 focus:ring-blue-500',
          
          'focus:outline-none focus:ring-1',
          
          // Disabled state
          disabled && 'opacity-50 cursor-not-allowed bg-gray-50 dark:bg-gray-900',
          
          // Read-only state
          readOnly && 'bg-gray-50 dark:bg-gray-900',
          
          // Size-based padding
          size === 'xs' && 'px-2 py-1 text-xs',
          size === 'sm' && 'px-3 py-1.5 text-sm',
          size === 'md' && 'px-3 py-2 text-sm',
          size === 'lg' && 'px-4 py-2.5 text-base',
          size === 'xl' && 'px-5 py-3 text-lg',
          
          // Resize behavior
          resizeClasses[resize],
          
          // Custom classes
          className
        )}
        {...(registration ? { ...registration, ref: registration.ref } : {})}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';
