/**
 * Rating Atom Component
 * Star rating display and input
 */

import React from 'react';
import { FiStar } from 'react-icons/fi';
import { cn } from '../utils';
import type { BaseComponentProps, Size } from '../types';

export interface RatingProps extends BaseComponentProps {
  /** Current rating value (0-max) */
  value: number;
  /** Maximum rating */
  max?: number;
  /** Rating change handler (if interactive) */
  onChange?: (value: number) => void;
  /** Whether rating is read-only */
  readOnly?: boolean;
  /** Size variant */
  size?: Extract<Size, 'sm' | 'md' | 'lg'>;
  /** Custom color for filled stars */
  color?: string;
  /** Show numeric value */
  showValue?: boolean;
}

const sizeConfig = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
};

export const Rating: React.FC<RatingProps> = ({
  value,
  max = 5,
  onChange,
  readOnly = false,
  size = 'md',
  color = 'text-yellow-500',
  showValue = false,
  className,
  testId,
  ariaLabel,
}) => {
  const [hoverValue, setHoverValue] = React.useState<number | null>(null);

  const handleClick = (newValue: number) => {
    if (!readOnly && onChange) {
      onChange(newValue);
    }
  };

  const handleMouseEnter = (index: number) => {
    if (!readOnly) {
      setHoverValue(index);
    }
  };

  const handleMouseLeave = () => {
    setHoverValue(null);
  };

  const displayValue = hoverValue !== null ? hoverValue : value;

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || `Rating: ${value} out of ${max} stars`}
      className={cn('flex items-center gap-0.5', className)}
    >
      {Array.from({ length: max }, (_, index) => {
        const starValue = index + 1;
        const isFilled = starValue <= displayValue;
        const isPartial = starValue - 0.5 <= displayValue && starValue > displayValue;

        return (
          <button
            key={index}
            type="button"
            onClick={() => handleClick(starValue)}
            onMouseEnter={() => handleMouseEnter(starValue)}
            onMouseLeave={handleMouseLeave}
            disabled={readOnly}
            className={cn(
              'relative transition-colors',
              !readOnly && 'cursor-pointer hover:scale-110',
              readOnly && 'cursor-default',
              sizeConfig[size]
            )}
            aria-label={`Rate ${starValue} out of ${max}`}
          >
            {/* Background star (empty) */}
            <FiStar
              className={cn(
                'absolute inset-0',
                sizeConfig[size],
                isFilled || isPartial ? color : 'text-gray-300 dark:text-gray-600'
              )}
              fill={isFilled ? 'currentColor' : 'none'}
            />
            
            {/* Partial star fill (if needed) */}
            {isPartial && (
              <div className="absolute inset-0 overflow-hidden" style={{ width: '50%' }}>
                <FiStar
                  className={cn('absolute inset-0', sizeConfig[size], color)}
                  fill="currentColor"
                />
              </div>
            )}
          </button>
        );
      })}

      {showValue && (
        <span className="ml-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          {value.toFixed(1)}
        </span>
      )}
    </div>
  );
};

Rating.displayName = 'Rating';
