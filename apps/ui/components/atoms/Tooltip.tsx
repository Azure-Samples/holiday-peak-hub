/**
 * Tooltip Atom Component
 * Contextual information on hover
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface TooltipProps extends BaseComponentProps {
  /** Tooltip content */
  content: React.ReactNode;
  /** Child element to trigger tooltip */
  children: React.ReactNode;
  /** Placement of tooltip */
  placement?: 'top' | 'right' | 'bottom' | 'left';
  /** Delay before showing (ms) */
  delay?: number;
}

const placementClasses = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
};

const arrowClasses = {
  top: 'top-full left-1/2 -translate-x-1/2 border-t-gray-900 dark:border-t-gray-100',
  right: 'right-full top-1/2 -translate-y-1/2 border-r-gray-900 dark:border-r-gray-100',
  bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-900 dark:border-b-gray-100',
  left: 'left-full top-1/2 -translate-y-1/2 border-l-gray-900 dark:border-l-gray-100',
};

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  placement = 'top',
  delay = 200,
  className,
  testId,
  ariaLabel,
}) => {
  const [visible, setVisible] = React.useState(false);
  const timeoutRef = React.useRef<NodeJS.Timeout>();

  const showTooltip = () => {
    timeoutRef.current = setTimeout(() => {
      setVisible(true);
    }, delay);
  };

  const hideTooltip = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setVisible(false);
  };

  React.useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <div
      className={cn('relative inline-block', className)}
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onFocus={showTooltip}
      onBlur={hideTooltip}
    >
      {children}
      
      {visible && (
        <div
          role="tooltip"
          data-testid={testId}
          aria-label={ariaLabel}
          className={cn(
            'absolute z-50 px-3 py-2 text-xs font-medium text-white bg-gray-900 dark:bg-gray-100 dark:text-gray-900 rounded-lg shadow-lg',
            'whitespace-nowrap pointer-events-none',
            'animate-in fade-in-0 zoom-in-95',
            placementClasses[placement]
          )}
        >
          {content}
          
          {/* Arrow */}
          <div
            className={cn(
              'absolute w-0 h-0 border-4 border-transparent',
              arrowClasses[placement]
            )}
          />
        </div>
      )}
    </div>
  );
};

Tooltip.displayName = 'Tooltip';
