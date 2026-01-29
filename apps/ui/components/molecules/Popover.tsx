/**
 * Popover Molecule Component
 * Floating content container
 */

import React from 'react';
import { Popover as HeadlessPopover, Transition } from '@headlessui/react';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface PopoverProps extends BaseComponentProps {
  /** Trigger button content */
  trigger: React.ReactNode;
  /** Popover content */
  children: React.ReactNode;
  /** Placement */
  placement?: 'top' | 'right' | 'bottom' | 'left';
  /** Custom button className */
  buttonClassName?: string;
}

const placementClasses = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
};

export const Popover: React.FC<PopoverProps> = ({
  trigger,
  children,
  placement = 'bottom',
  buttonClassName,
  className,
  testId,
  ariaLabel,
}) => {
  return (
    <HeadlessPopover className={cn('relative', className)} data-testid={testId}>
      <HeadlessPopover.Button
        className={cn(
          'inline-flex items-center gap-2 px-4 py-2 text-sm font-medium',
          'rounded-lg transition-colors',
          'text-gray-700 dark:text-gray-300',
          'hover:bg-gray-100 dark:hover:bg-gray-800',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
          'dark:focus:ring-offset-gray-900',
          buttonClassName
        )}
        aria-label={ariaLabel}
      >
        {trigger}
      </HeadlessPopover.Button>

      <Transition
        enter="transition ease-out duration-200"
        enterFrom="opacity-0 translate-y-1"
        enterTo="opacity-100 translate-y-0"
        leave="transition ease-in duration-150"
        leaveFrom="opacity-100 translate-y-0"
        leaveTo="opacity-0 translate-y-1"
      >
        <HeadlessPopover.Panel
          className={cn(
            'absolute z-50',
            'bg-white dark:bg-gray-800',
            'border border-gray-200 dark:border-gray-700',
            'rounded-lg shadow-lg',
            'min-w-[200px] max-w-sm',
            placementClasses[placement]
          )}
        >
          <div className="p-4">{children}</div>
        </HeadlessPopover.Panel>
      </Transition>
    </HeadlessPopover>
  );
};

Popover.displayName = 'Popover';
