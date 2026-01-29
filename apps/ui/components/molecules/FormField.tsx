/**
 * FormField Molecule Component
 * Unified form field that composes Label + Input/Select/Textarea + Error + Hint
 * Consolidates patterns from forms/ and react-hook-form/
 */

import React from 'react';
import { cn } from '../utils';
import { Label } from '../atoms/Label';
import { Input, InputProps } from '../atoms/Input';
import { Select, SelectProps } from '../atoms/Select';
import { Textarea, TextareaProps } from '../atoms/Textarea';
import type { FormFieldBaseProps } from '../types';

export interface FormFieldProps extends FormFieldBaseProps {
  /** Field type */
  fieldType?: 'input' | 'select' | 'textarea';
  /** Props to pass to the input/select/textarea */
  fieldProps?: Partial<InputProps | SelectProps | TextareaProps>;
  /** Whether to show character count (for input/textarea) */
  showCharCount?: boolean;
  /** Max characters (for character count) */
  maxLength?: number;
}

export const FormField: React.FC<FormFieldProps> = ({
  name,
  label,
  placeholder,
  error,
  hint,
  success,
  required = false,
  disabled = false,
  fieldType = 'input',
  fieldProps = {},
  showCharCount = false,
  maxLength,
  className,
  testId,
  ariaLabel,
}) => {
  const [charCount, setCharCount] = React.useState(0);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    if (showCharCount) {
      setCharCount(e.target.value.length);
    }
    if (fieldProps.onChange) {
      fieldProps.onChange(e as any);
    }
  };

  const renderField = () => {
    const commonProps = {
      name,
      placeholder,
      disabled,
      required,
      error,
      testId: `${testId}-field`,
      ariaLabel,
      ...fieldProps,
    };

    switch (fieldType) {
      case 'select':
        return <Select {...(commonProps as SelectProps)} />;
      
      case 'textarea':
        return (
          <Textarea
            {...(commonProps as TextareaProps)}
            maxLength={maxLength}
            onChange={handleInputChange}
          />
        );
      
      case 'input':
      default:
        return (
          <Input
            {...(commonProps as InputProps)}
            maxLength={maxLength}
            onChange={handleInputChange}
          />
        );
    }
  };

  return (
    <div data-testid={testId} className={cn('space-y-1', className)}>
      {label && (
        <Label
          htmlFor={name}
          required={required}
          testId={`${testId}-label`}
        >
          {label}
        </Label>
      )}

      {renderField()}

      <div className="flex items-center justify-between">
        <div className="flex-1">
          {error && (
            <p
              className="text-xs text-red-600 dark:text-red-400"
              role="alert"
              id={`${name}-error`}
            >
              {error}
            </p>
          )}

          {!error && success && (
            <p
              className="text-xs text-green-600 dark:text-green-400"
              role="status"
              id={`${name}-success`}
            >
              {success}
            </p>
          )}

          {!error && !success && hint && (
            <p
              className="text-xs text-gray-500 dark:text-gray-400"
              id={`${name}-hint`}
            >
              {hint}
            </p>
          )}
        </div>

        {showCharCount && maxLength && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {charCount}/{maxLength}
          </p>
        )}
      </div>
    </div>
  );
};

FormField.displayName = 'FormField';
