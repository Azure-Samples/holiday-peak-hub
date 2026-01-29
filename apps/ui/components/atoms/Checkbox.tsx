/**
 * Checkbox Atom Component
 * Checkbox input with label and react-hook-form support
 */

import React, { forwardRef } from 'react';
import { useFormContext } from 'react-hook-form';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface CheckboxProps extends BaseComponentProps {
  /** Checkbox name */
  name: string;
  /** Checkbox label */
  label: string;
  /** Whether checkbox is checked (controlled) */
  checked?: boolean;
  /** Default checked state */
  defaultChecked?: boolean;
  /** Change handler */
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** Whether checkbox is disabled */
  disabled?: boolean;
  /** Whether checkbox is required */
  required?: boolean;
  /** Whether checkbox is in indeterminate state */
  indeterminate?: boolean;
  /** Whether to use react-hook-form integration */
  useRHF?: boolean;
  /** Validation rules for react-hook-form */
  rules?: any;
  /** Helper text below label */
  hint?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  (
    {
      name,
      label,
      checked,
      defaultChecked,
      onChange,
      disabled = false,
      required = false,
      indeterminate = false,
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

    // Handle indeterminate state
    const checkboxRef = React.useRef<HTMLInputElement>(null);
    React.useEffect(() => {
      if (checkboxRef.current) {
        checkboxRef.current.indeterminate = indeterminate;
      }
    }, [indeterminate]);

    return (
      <div className={cn('flex items-start space-x-2', className)}>
        <div className="flex items-center h-6">
          <input
            ref={(e) => {
              // Handle both forwarded ref and internal ref for indeterminate
              if (typeof ref === 'function') ref(e);
              else if (ref) ref.current = e;
              (checkboxRef as any).current = e;
              if (registration) registration.ref(e);
            }}
            type="checkbox"
            name={name}
            checked={checked}
            defaultChecked={defaultChecked}
            onChange={onChange}
            disabled={disabled}
            required={required}
            data-testid={testId}
            aria-label={ariaLabel || label}
            aria-required={required}
            aria-describedby={hint ? `${name}-hint` : undefined}
            className={cn(
              'w-4 h-4 rounded',
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
            htmlFor={name}
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
              id={`${name}-hint`}
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

Checkbox.displayName = 'Checkbox';
