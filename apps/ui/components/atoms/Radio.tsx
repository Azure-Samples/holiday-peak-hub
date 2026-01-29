/**
 * Radio Atom Component
 * Radio button input with label and react-hook-form support
 */

import React, { forwardRef } from 'react';
import { useFormContext } from 'react-hook-form';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface RadioProps extends BaseComponentProps {
  /** Radio name (group identifier) */
  name: string;
  /** Radio value */
  value: string | number;
  /** Radio label */
  label: string;
  /** Whether radio is checked (controlled) */
  checked?: boolean;
  /** Default checked state */
  defaultChecked?: boolean;
  /** Change handler */
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** Whether radio is disabled */
  disabled?: boolean;
  /** Whether radio is required */
  required?: boolean;
  /** Whether to use react-hook-form integration */
  useRHF?: boolean;
  /** Validation rules for react-hook-form */
  rules?: any;
  /** Helper text below label */
  hint?: string;
}

export const Radio = forwardRef<HTMLInputElement, RadioProps>(
  (
    {
      name,
      value,
      label,
      checked,
      defaultChecked,
      onChange,
      disabled = false,
      required = false,
      useRHF = false,
      rules,
      hint,
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

    return (
      <div className={cn('flex items-start space-x-2', className)}>
        <div className="flex items-center h-6">
          <input
            ref={registration ? registration.ref : ref}
            type="radio"
            name={name}
            value={value}
            checked={checked}
            defaultChecked={defaultChecked}
            onChange={onChange}
            disabled={disabled}
            required={required}
            data-testid={testId}
            aria-label={ariaLabel || label}
            aria-required={required}
            aria-describedby={hint ? `${name}-${value}-hint` : undefined}
            className={cn(
              'w-4 h-4',
              'text-blue-600 bg-white dark:bg-gray-800',
              'border-gray-300 dark:border-gray-700',
              'focus:ring-2 focus:ring-blue-500 focus:ring-offset-0',
              'transition-colors duration-200',
              'cursor-pointer',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
            {...(registration ? { ...registration, ref: registration.ref } : {})}
            {...props}
          />
        </div>
        
        <div className="text-sm space-y-1">
          <label
            htmlFor={`${name}-${value}`}
            className={cn(
              'block font-medium select-none',
              'text-gray-700 dark:text-white',
              disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
            )}
          >
            {label}
            {required && (
              <span className="ml-1 text-red-500" aria-label="required">
                *
              </span>
            )}
          </label>
          
          {hint && (
            <p
              id={`${name}-${value}-hint`}
              className="text-xs text-gray-500 dark:text-gray-400"
            >
              {hint}
            </p>
          )}
        </div>
      </div>
    );
  }
);

Radio.displayName = 'Radio';
