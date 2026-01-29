/**
 * Input Atom Component
 * Text input with support for variants, validation states, and react-hook-form
 */

import React, { forwardRef } from 'react';
import { useFormContext } from 'react-hook-form';
import { cn, sizeClasses } from '../utils';
import type { Size, FormFieldBaseProps, InputType } from '../types';

export interface InputProps extends Omit<FormFieldBaseProps, 'label' | 'hint'> {
  /** Input type */
  type?: InputType;
  /** Input size */
  size?: Size;
  /** Default value */
  defaultValue?: string | number;
  /** Current value (controlled) */
  value?: string | number;
  /** Change handler */
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** Blur handler */
  onBlur?: (e: React.FocusEvent<HTMLInputElement>) => void;
  /** Icon or element to show before input */
  prefix?: React.ReactNode;
  /** Icon or element to show after input */
  suffix?: React.ReactNode;
  /** Whether to use react-hook-form integration */
  useRHF?: boolean;
  /** Validation rules for react-hook-form */
  rules?: any;
  /** Min value (for number inputs) */
  min?: number;
  /** Max value (for number inputs) */
  max?: number;
  /** Step value (for number inputs) */
  step?: number;
  /** Pattern for validation */
  pattern?: string;
  /** Max length */
  maxLength?: number;
  /** Whether input is read-only */
  readOnly?: boolean;
  /** Autocomplete attribute */
  autoComplete?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      type = 'text',
      name,
      size = 'md',
      placeholder,
      defaultValue,
      value,
      onChange,
      onBlur,
      disabled = false,
      required = false,
      error,
      prefix,
      suffix,
      useRHF = false,
      rules,
      className,
      testId,
      ariaLabel,
      min,
      max,
      step,
      pattern,
      maxLength,
      readOnly = false,
      autoComplete,
      ...props
    },
    ref
  ) => {
    // React Hook Form integration
    const formContext = useRHF ? useFormContext() : null;
    const registration = formContext && name ? formContext.register(name, rules) : null;

    const hasError = error || (formContext?.formState.errors[name] && true);
    const hasPrefix = !!prefix;
    const hasSuffix = !!suffix;

    const inputElement = (
      <input
        ref={registration ? registration.ref : ref}
        type={type}
        name={name}
        placeholder={placeholder}
        defaultValue={defaultValue}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        disabled={disabled}
        required={required}
        min={min}
        max={max}
        step={step}
        pattern={pattern}
        maxLength={maxLength}
        readOnly={readOnly}
        autoComplete={autoComplete}
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
          
          // Size variants
          sizeClasses.input[size],
          
          // Padding adjustments for prefix/suffix
          hasPrefix && 'pl-10',
          hasSuffix && 'pr-10',
          
          // Custom classes
          className
        )}
        {...(registration ? { ...registration, ref: registration.ref } : {})}
        {...props}
      />
    );

    // If no prefix/suffix, return simple input
    if (!hasPrefix && !hasSuffix) {
      return inputElement;
    }

    // Return input with prefix/suffix wrapper
    return (
      <div className="relative">
        {prefix && (
          <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
            <span className="text-gray-400 dark:text-gray-500">{prefix}</span>
          </div>
        )}
        
        {inputElement}
        
        {suffix && (
          <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <span className="text-gray-400 dark:text-gray-500">{suffix}</span>
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
