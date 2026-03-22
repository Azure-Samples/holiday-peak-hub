/**
 * MainLayout Template
 * Primary layout for all pages with navigation and footer
 */

'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '../utils';
import { Navigation } from '../organisms/Navigation';
import type { BaseComponentProps } from '../types';
import type { NavigationProps } from '../organisms/Navigation';

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
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const handleMobileMenuToggle = React.useCallback(() => {
    setMobileMenuOpen((previousState) => !previousState);
  }, []);

  const handleSearch = (query: string) => {
    const trimmed = query.trim();
    if (trimmed) {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };
  const hasExternalMobileMenuController =
    typeof navigationProps?.mobileMenuOpen === 'boolean'
    && typeof navigationProps?.onMobileMenuToggle === 'function';

  const mergedNavigationProps = {
    ...navigationProps,
    onSearch: navigationProps?.onSearch ?? handleSearch,
    mobileMenuOpen: hasExternalMobileMenuController
      ? navigationProps?.mobileMenuOpen
      : mobileMenuOpen,
    onMobileMenuToggle: hasExternalMobileMenuController
      ? navigationProps?.onMobileMenuToggle
      : handleMobileMenuToggle,
  };
  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Main layout'}
      className={cn(
        'min-h-screen flex flex-col',
        backgroundColor || 'bg-transparent',
        className
      )}
    >
      {showNavigation && <Navigation {...mergedNavigationProps} />}

      <main id="main-content" className="flex-1" role="main">
        {fullWidth ? (
          children
        ) : (
          <div className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6 sm:py-8 lg:px-8">
            {children}
          </div>
        )}
      </main>

      {showFooter && footer && (
        <footer className="border-t border-[var(--hp-border)] bg-[var(--hp-surface)]/80">
          {footer}
        </footer>
      )}
    </div>
  );
};

MainLayout.displayName = 'MainLayout';
