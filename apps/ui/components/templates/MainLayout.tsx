/**
 * MainLayout Template
 * Primary layout for all pages with navigation and footer
 */

import React from 'react';
import { cn } from '../utils';
import { Navigation } from '../organisms/Navigation';
import type { NavigationProps, BaseComponentProps } from '../types';

export interface MainLayoutProps extends BaseComponentProps {
  /** Navigation props */
  navigationProps?: Omit<NavigationProps, 'className'>;
  /** Page content */
  children: React.ReactNode;
  /** Footer component */
  footer?: React.ReactNode;
  /** Show navigation */
  showNavigation?: boolean;
  /** Show footer */
  showFooter?: boolean;
  /** Full width content (no max-width container) */
  fullWidth?: boolean;
  /** Background color */
  backgroundColor?: string;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  navigationProps,
  children,
  footer,
  showNavigation = true,
  showFooter = true,
  fullWidth = false,
  backgroundColor,
  className,
  testId,
  ariaLabel,
}) => {
  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Main layout'}
      className={cn(
        'min-h-screen flex flex-col',
        backgroundColor || 'bg-gray-50 dark:bg-gray-900',
        className
      )}
    >
      {/* Navigation */}
      {showNavigation && <Navigation {...navigationProps} />}

      {/* Main Content */}
      <main className="flex-1">
        {fullWidth ? (
          children
        ) : (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </div>
        )}
      </main>

      {/* Footer */}
      {showFooter && footer && (
        <footer className="border-t border-gray-200 dark:border-gray-800">
          {footer}
        </footer>
      )}
    </div>
  );
};

MainLayout.displayName = 'MainLayout';
