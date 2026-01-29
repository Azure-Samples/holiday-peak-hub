/**
 * Steps Molecule Component
 * Step-by-step progress indicator
 */

import React from 'react';
import { FiCheck } from 'react-icons/fi';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface Step {
  id: string;
  title: string;
  description?: string;
  completed?: boolean;
}

export interface StepsProps extends BaseComponentProps {
  /** Array of steps */
  steps: Step[];
  /** Current active step index */
  currentStep: number;
  /** Step click handler */
  onStepClick?: (index: number) => void;
  /** Orientation */
  orientation?: 'horizontal' | 'vertical';
  /** Allow clicking completed steps */
  clickable?: boolean;
}

export const Steps: React.FC<StepsProps> = ({
  steps,
  currentStep,
  onStepClick,
  orientation = 'horizontal',
  clickable = true,
  className,
  testId,
  ariaLabel,
}) => {
  const isHorizontal = orientation === 'horizontal';

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Steps indicator'}
      className={cn(
        'flex',
        isHorizontal ? 'flex-row items-center' : 'flex-col',
        className
      )}
    >
      {steps.map((step, index) => {
        const isActive = index === currentStep;
        const isCompleted = step.completed || index < currentStep;
        const isClickable = clickable && (isCompleted || isActive);

        return (
          <React.Fragment key={step.id}>
            {/* Step */}
            <div
              className={cn(
                'flex items-center',
                isHorizontal ? 'flex-col' : 'flex-row',
                'flex-shrink-0'
              )}
            >
              <button
                onClick={() => isClickable && onStepClick?.(index)}
                disabled={!isClickable}
                className={cn(
                  'relative flex items-center justify-center',
                  'w-10 h-10 rounded-full border-2 transition-all',
                  'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                  'dark:focus:ring-offset-gray-900',
                  isCompleted && [
                    'bg-blue-600 border-blue-600 text-white',
                    isClickable && 'hover:bg-blue-700 hover:border-blue-700',
                  ],
                  isActive && [
                    'bg-white dark:bg-gray-900 border-blue-600 text-blue-600',
                    'shadow-lg',
                  ],
                  !isActive && !isCompleted && [
                    'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-gray-500',
                  ],
                  isClickable ? 'cursor-pointer' : 'cursor-default'
                )}
              >
                {isCompleted ? (
                  <FiCheck className="w-5 h-5" />
                ) : (
                  <span className="text-sm font-semibold">{index + 1}</span>
                )}
              </button>

              {/* Step label */}
              <div
                className={cn(
                  'flex flex-col',
                  isHorizontal ? 'items-center mt-2' : 'ml-4'
                )}
              >
                <span
                  className={cn(
                    'text-sm font-medium',
                    isActive || isCompleted
                      ? 'text-gray-900 dark:text-white'
                      : 'text-gray-500 dark:text-gray-400'
                  )}
                >
                  {step.title}
                </span>
                {step.description && (
                  <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {step.description}
                  </span>
                )}
              </div>
            </div>

            {/* Connector */}
            {index < steps.length - 1 && (
              <div
                className={cn(
                  'flex-1 transition-colors',
                  isHorizontal
                    ? 'h-0.5 mx-2 min-w-[40px]'
                    : 'w-0.5 ml-5 my-2 min-h-[40px]',
                  index < currentStep
                    ? 'bg-blue-600'
                    : 'bg-gray-300 dark:bg-gray-700'
                )}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

Steps.displayName = 'Steps';
