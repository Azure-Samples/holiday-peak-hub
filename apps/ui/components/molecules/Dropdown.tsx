/**
 * Dropdown Molecule Component
 * Unified dropdown menu using Headless UI
 * Consolidates 9 different dropdown implementations
 */

import React from 'react';
import { Menu, MenuButton, MenuItems, MenuItem, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { FiChevronDown } from 'react-icons/fi';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface DropdownItem {
  key: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  onClick?: () => void;
  href?: string;
  disabled?: boolean;
  divider?: boolean;
}

export interface DropdownProps extends BaseComponentProps {
  /** Dropdown trigger content */
  trigger: React.ReactNode;
  /** Dropdown items */
  items: DropdownItem[];
  /** Dropdown placement */
  placement?: 'left' | 'right';
  /** Custom trigger button class */
  triggerClassName?: string;
  /** Whether to show chevron icon */
  showChevron?: boolean;
  /** Custom menu width */
  menuWidth?: string;
  /** Whether trigger is icon-only button */
  iconButton?: boolean;
}

export const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  items,
  placement = 'right',
  triggerClassName,
  showChevron = false,
  menuWidth = 'w-56',
  iconButton = false,
  className,
  testId,
  ariaLabel,
}) => {
  return (
    <Menu as="div" className={cn('relative inline-block text-left', className)} data-testid={testId}>
      <div>
        <MenuButton
          aria-label={ariaLabel}
          className={cn(
            'inline-flex items-center justify-center',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
            'transition-colors duration-200',
            iconButton
              ? 'w-8 h-8 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800'
              : 'px-4 py-2 text-sm font-semibold text-gray-900 dark:text-white bg-white dark:bg-gray-800 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700',
            triggerClassName
          )}
        >
          {({ open }) => (
            <>
              {trigger}
              {showChevron && (
                <FiChevronDown
                  className={cn(
                    'ml-2 w-4 h-4 transition-transform duration-200',
                    open && 'rotate-180'
                  )}
                />
              )}
            </>
          )}
        </MenuButton>
      </div>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <MenuItems
          className={cn(
            'absolute mt-2 origin-top-right',
            menuWidth,
            placement === 'left' ? 'left-0 origin-top-left' : 'right-0 origin-top-right',
            'bg-white dark:bg-gray-800',
            'text-gray-900 dark:text-white',
            'shadow-lg rounded-md',
            'ring-1 ring-black ring-opacity-5',
            'divide-y divide-gray-100 dark:divide-gray-700',
            'focus:outline-none',
            'z-50'
          )}
        >
          <div className="py-1">
            {items.map((item) => {
              if (item.divider) {
                return (
                  <div
                    key={item.key}
                    className="my-1 border-t border-gray-100 dark:border-gray-700"
                  />
                );
              }

              return (
                <MenuItem key={item.key} disabled={item.disabled}>
                  {({ active }) => (
                    item.href ? (
                      <a
                        href={item.href}
                        className={cn(
                          'flex items-center w-full px-4 py-2 text-sm',
                          active
                            ? 'bg-blue-500 text-white'
                            : 'text-gray-900 dark:text-white',
                          item.disabled && 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        {item.icon && <span className="mr-3">{item.icon}</span>}
                        {item.label}
                      </a>
                    ) : (
                      <button
                        type="button"
                        onClick={item.onClick}
                        disabled={item.disabled}
                        className={cn(
                          'flex items-center w-full px-4 py-2 text-sm text-left',
                          active
                            ? 'bg-blue-500 text-white'
                            : 'text-gray-900 dark:text-white',
                          item.disabled && 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        {item.icon && <span className="mr-3">{item.icon}</span>}
                        {item.label}
                      </button>
                    )
                  )}
                </MenuItem>
              );
            })}
          </div>
        </MenuItems>
      </Transition>
    </Menu>
  );
};

Dropdown.displayName = 'Dropdown';
