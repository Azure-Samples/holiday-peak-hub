/**
 * Radio Atom Component
 * Radio button input with label and react-hook-form support
 */

import React, { forwardRef } from 'react';
import { useFormContext } from 'react-hook-form';
import type { RegisterOptions } from 'react-hook-form';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface RadioProps extends BaseComponentProps {
  /** Radio name (group identifier) */
  name?: string;
  /** Radio value */
  value?: string | number;
  /** Radio label */
  label?: React.ReactNode;
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
  rules?: RegisterOptions;
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
    const rawCtx = useFormContext();  // Always call hook unconditionally
    const formContext = useRHF ? rawCtx : null;
    const resolvedName = name || `radio-${testId || 'group'}`;
    const resolvedValue = value ?? '';
    const registration = formContext && resolvedName ? formContext.register(resolvedName, rules) : null;
    const inputId = `${resolvedName}-${String(resolvedValue)}`;

    return (
      <div className={cn('flex items-start space-x-2', className)}>
        <div className="flex items-center h-6">
          <input
            ref={registration ? registration.ref : ref}
            type="radio"
            name={resolvedName}
            id={inputId}
            value={resolvedValue}
            checked={checked}
            defaultChecked={defaultChecked}
            onChange={(event) => {
              registration?.onChange(event);
              onChange?.(event);
            }}
            onBlur={(event) => {
              registration?.onBlur(event);
            }}
            disabled={disabled}
            required={required}
            data-testid={testId}
            aria-label={ariaLabel || (typeof label === 'string' ? label : undefined)}
            aria-describedby={hint ? `${resolvedName}-${String(resolvedValue)}-hint` : undefined}
            className={cn(
              'w-4 h-4',
              'text-blue-600 bg-white dark:bg-gray-800',
              'border-gray-300 dark:border-gray-700',
              'focus:ring-2 focus:ring-blue-500 focus:ring-offset-0',
              'transition-colors duration-200',
              'cursor-pointer',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
            {...props}
          />
        </div>
        
        <div className="text-sm space-y-1">
          <label
            htmlFor={inputId}
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
              id={`${resolvedName}-${String(resolvedValue)}-hint`}
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
