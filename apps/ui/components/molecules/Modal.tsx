/**
 * Modal Molecule Component
 * Dialog component using Headless UI
 * Consolidates modal-1, modal-2, modal-3 implementations
 */

import React from 'react';
import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from '@headlessui/react';
import { Fragment } from 'react';
import { FiX } from 'react-icons/fi';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface ModalProps extends BaseComponentProps {
  /** Whether modal is open */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Modal title */
  title?: string;
  /** Modal content */
  children: React.ReactNode;
  /** Footer content (buttons, actions) */
  footer?: React.ReactNode;
  /** Modal size */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /** Whether to show close button */
  showCloseButton?: boolean;
  /** Whether clicking overlay closes modal */
  closeOnOverlayClick?: boolean;
  /** Icon to show in header */
  icon?: React.ReactNode;
  /** Icon background color */
  iconBgColor?: string;
  /** Whether modal is centered vertically */
  centered?: boolean;
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-7xl',
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  showCloseButton = true,
  closeOnOverlayClick = true,
  icon,
  iconBgColor = 'bg-blue-100 dark:bg-blue-900',
  centered = true,
  className,
  testId,
  ariaLabel,
}) => {
  const handleOverlayClick = () => {
    if (closeOnOverlayClick) {
      onClose();
    }
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog
        as="div"
        className="relative z-50"
        onClose={handleOverlayClick}
        data-testid={testId}
      >
        {/* Backdrop */}
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/25 dark:bg-black/50" />
        </TransitionChild>

        {/* Modal container */}
        <div className="fixed inset-0 overflow-y-auto">
          <div
            className={cn(
              'flex min-h-full p-4 text-center',
              centered ? 'items-center justify-center' : 'items-start justify-center pt-16'
            )}
          >
            <TransitionChild
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <DialogPanel
                className={cn(
                  'relative w-full transform overflow-hidden',
                  'bg-white dark:bg-gray-800',
                  'text-left align-middle shadow-xl transition-all',
                  'rounded-2xl',
                  sizeClasses[size],
                  className
                )}
              >
                {/* Header */}
                {(title || icon || showCloseButton) && (
                  <div className="relative px-6 pt-6 pb-4">
                    {icon && (
                      <div
                        className={cn(
                          'mx-auto flex h-12 w-12 items-center justify-center rounded-full mb-4',
                          iconBgColor
                        )}
                      >
                        {icon}
                      </div>
                    )}

                    {title && (
                      <DialogTitle
                        as="h3"
                        className={cn(
                          'text-lg font-semibold leading-6',
                          'text-gray-900 dark:text-white',
                          icon && 'text-center'
                        )}
                      >
                        {title}
                      </DialogTitle>
                    )}

                    {showCloseButton && (
                      <button
                        type="button"
                        onClick={onClose}
                        className={cn(
                          'absolute top-4 right-4',
                          'rounded-md p-1',
                          'text-gray-400 hover:text-gray-500',
                          'dark:text-gray-500 dark:hover:text-gray-400',
                          'hover:bg-gray-100 dark:hover:bg-gray-700',
                          'focus:outline-none focus:ring-2 focus:ring-blue-500'
                        )}
                        aria-label="Close modal"
                      >
                        <FiX className="h-5 w-5" />
                      </button>
                    )}
                  </div>
                )}

                {/* Body */}
                <div className="px-6 py-4">
                  {children}
                </div>

                {/* Footer */}
                {footer && (
                  <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 rounded-b-2xl">
                    {footer}
                  </div>
                )}
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
};

Modal.displayName = 'Modal';
