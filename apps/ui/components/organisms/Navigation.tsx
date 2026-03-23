/**
 * Navigation Organism Component
 * Main application navigation bar with Ocean Blue/Lime Green/Cyan theme
 */

import React from 'react';
import Link from 'next/link';
import {
  FiShoppingCart,
  FiHeart,
  FiUser,
  FiMenu,
  FiSearch,
  FiMessageSquare,
} from 'react-icons/fi';
import { cn } from '../utils';
import { Button } from '../atoms/Button';
import { Badge } from '../atoms/Badge';
import { ThemeToggle } from '../atoms/ThemeToggle';
import { SearchInput } from '../molecules/SearchInput';
import { Dropdown, DropdownItem } from '../molecules/Dropdown';
import type { BaseComponentProps } from '../types';
import { useAgentGlobalHealth } from '@/lib/hooks/useAgentMonitor';
import { useAuth } from '@/contexts/AuthContext';
import { isDevAuthMockUiEnabled } from '@/lib/auth/msalConfig';

export interface NavigationProps extends BaseComponentProps {
  /** Logo component or image */
  logo?: React.ReactNode;
  /** Search handler */
  onSearch?: (query: string) => void;
  /** Cart item count */
  cartCount?: number;
  /** Wishlist item count */
  wishlistCount?: number;
  /** Whether user is logged in */
  isLoggedIn?: boolean;
  /** User name (if logged in) */
  userName?: string;
  /** User avatar URL */
  userAvatar?: string;
  /** Navigation links */
  navLinks?: Array<{ label: string; href: string; }>;
  /** User menu items */
  userMenuItems?: DropdownItem[];
  /** Mobile menu open state */
  mobileMenuOpen?: boolean;
  /** Mobile menu toggle handler */
  onMobileMenuToggle?: () => void;
  /** Whether navigation is sticky */
  sticky?: boolean;
  /** Background transparency (for hero sections) */
  transparent?: boolean;
}

export const Navigation: React.FC<NavigationProps> = ({
  logo,
  onSearch,
  cartCount = 0,
  wishlistCount = 0,
  isLoggedIn = false,
  userName,
  userAvatar,
  navLinks = [
    { label: 'Catalog', href: '/category?slug=all' },
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Admin', href: '/admin' },
    { label: 'Search Demo', href: '/search' },
    { label: 'Product Demo', href: '/product?id=prd_001' },
  ],
  userMenuItems = [
    { key: 'profile', label: 'My Profile', href: '/profile' },
    { key: 'orders', label: 'My Orders', href: '/orders' },
    { key: 'wishlist', label: 'Wishlist', href: '/wishlist' },
    { key: 'divider', divider: true },
    { key: 'settings', label: 'Settings', href: '/settings' },
    { key: 'logout', label: 'Logout', href: '/logout' },
  ],
  mobileMenuOpen = false,
  onMobileMenuToggle,
  sticky = true,
  transparent = false,
  className,
  testId,
  ariaLabel,
}) => {
  const { isAuthenticated, loginAsMockRole, user } = useAuth();
  let globalHealth: 'healthy' | 'degraded' | 'down' | 'unknown' | undefined;

  try {
    const healthQuery = useAgentGlobalHealth();
    globalHealth = healthQuery.data;
  } catch {
    globalHealth = 'unknown';
  }

  const healthIndicatorClass =
    globalHealth === 'healthy'
      ? 'bg-green-500'
      : globalHealth === 'degraded'
        ? 'bg-yellow-500'
        : globalHealth === 'down'
          ? 'bg-red-500'
          : 'bg-gray-500';

  const navBackground = transparent
    ? 'bg-transparent'
    : 'bg-[var(--hp-surface)]/95 backdrop-blur border-b border-[var(--hp-border)]';

  const showMockRoleQuickLogin = isDevAuthMockUiEnabled && !isAuthenticated;
  const effectiveIsLoggedIn = isLoggedIn || isAuthenticated;
  const effectiveUserName = userName || user?.name;

  const handleMockRoleLogin = async (role: 'customer' | 'staff' | 'admin') => {
    try {
      await loginAsMockRole(role);
    } catch (error) {
      console.error('Mock role login failed:', error);
    }
  };

  const handleMobileLinkClick = () => {
    onMobileMenuToggle?.();
  };

  return (
    <nav
      data-testid={testId}
      aria-label={ariaLabel || 'Main navigation'}
      className={cn(
        'w-full z-50 transition-colors duration-200',
        sticky && 'sticky top-0',
        navBackground,
        className
      )}
    >
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-[60] focus:bg-[var(--hp-surface)] focus:px-3 focus:py-2">
          Skip to content
        </a>

        <div className="flex min-h-16 items-center justify-between gap-3 py-2">
          <div className="flex items-center gap-2 xl:hidden">
            <Button
              variant="ghost"
              size="sm"
              iconOnly
              onClick={onMobileMenuToggle}
              ariaLabel={mobileMenuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-menu"
              className="text-[var(--hp-text)]"
            >
              <FiMenu className="w-6 h-6" />
            </Button>
          </div>

          <div className="flex flex-1 items-center gap-3 lg:flex-none">
            <Link href="/" className="flex items-center space-x-2" aria-label="Holiday Peak home">
              {logo || (
                <>
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--hp-primary)] text-white shadow-sm">
                    <FiShoppingCart className="h-5 w-5" />
                  </div>
                  <span className="text-lg font-black tracking-tight text-[var(--hp-text)] sm:text-xl">
                    Holiday Peak
                  </span>
                </>
              )}
            </Link>
          </div>

          <div className="hidden xl:flex xl:items-center xl:space-x-5" aria-label="Catalog sections">
            {navLinks.map((link) => (
              <Link
                key={`${link.href}-${link.label}`}
                href={link.href}
                className="rounded-md px-2 py-1 text-sm font-semibold text-[var(--hp-text-muted)] transition-colors hover:text-[var(--hp-primary)]"
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="hidden xl:flex xl:flex-1 xl:max-w-md xl:mx-4">
            <SearchInput
              placeholder="Search catalog products"
              onSearch={onSearch}
              size="sm"
              className="w-full"
            />
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            <Link
              href="/admin/enrichment-monitor"
              className="hidden items-center gap-1 rounded-full border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-[var(--hp-text)] md:inline-flex"
              aria-label="Open enrichment pipeline monitor"
            >
              <span aria-hidden="true" className={`h-2 w-2 rounded-full ${healthIndicatorClass}`} />
              Pipeline Status
            </Link>

            <Link
              href="/search?agentChat=1"
              className="hidden rounded-full border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-[var(--hp-primary)] md:inline-flex"
              aria-label="Open product enrichment agent chat"
            >
              <FiMessageSquare className="mr-1 h-4 w-4" />
              Agent
            </Link>

            <ThemeToggle size="sm" />

            <div className="xl:hidden">
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                ariaLabel="Search catalog"
                onClick={() => onSearch?.('')}
              >
                <FiSearch className="w-5 h-5" />
              </Button>
            </div>

            <Link href="/wishlist">
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                ariaLabel="Wishlist"
                className="relative"
              >
                <FiHeart className="w-5 h-5" />
                {wishlistCount > 0 && (
                  <span className="absolute -top-1 -right-1">
                    <Badge variant="error" dot size="sm">
                      {wishlistCount}
                    </Badge>
                  </span>
                )}
              </Button>
            </Link>

            <Link href="/cart">
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                ariaLabel="Shopping cart"
                className="relative"
              >
                <FiShoppingCart className="w-5 h-5" />
                {cartCount > 0 && (
                  <span className="absolute -top-1 -right-1">
                    <Badge size="sm" className="bg-[var(--hp-accent)] text-white">
                      {cartCount}
                    </Badge>
                  </span>
                )}
              </Button>
            </Link>

            {effectiveIsLoggedIn ? (
              <Dropdown
                trigger={
                  userAvatar ? (
                    <img
                      src={userAvatar}
                      alt={effectiveUserName || 'User'}
                      className="w-8 h-8 rounded-full"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-[var(--hp-primary)] flex items-center justify-center text-white text-sm font-semibold">
                      {effectiveUserName?.charAt(0)?.toUpperCase() || 'U'}
                    </div>
                  )
                }
                items={userMenuItems}
                placement="right"
                iconButton
              />
            ) : (
              <div className="flex items-center gap-2">
                {showMockRoleQuickLogin ? (
                  <div className="hidden items-center gap-1 md:flex">
                    <Button variant="secondary" size="sm" onClick={() => void handleMockRoleLogin('customer')}>
                      Customer
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => void handleMockRoleLogin('staff')}>
                      Staff
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => void handleMockRoleLogin('admin')}>
                      Admin
                    </Button>
                  </div>
                ) : null}
                <Link href="/auth/login">
                  <Button
                    variant="primary"
                    size="sm"
                    iconLeft={<FiUser className="w-4 h-4" />}
                    className="bg-[var(--hp-primary)] hover:bg-[var(--hp-primary-hover)]"
                  >
                    Sign In
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div
          id="mobile-menu"
          className="xl:hidden border-t border-[var(--hp-border)] bg-[var(--hp-surface)] showcase-rise"
        >
          <div className="space-y-2 px-4 py-3">
            <div className="pb-3">
              <SearchInput
                placeholder="Search catalog products"
                onSearch={onSearch}
                size="sm"
                className="w-full"
              />
            </div>

            <Link
              href="/search?agentChat=1"
              className="flex items-center rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-3 py-2 text-sm font-semibold text-[var(--hp-primary)]"
              onClick={handleMobileLinkClick}
            >
              <FiMessageSquare className="mr-2 h-4 w-4" />
              Open Agent Popup
            </Link>

            {showMockRoleQuickLogin ? (
              <div className="grid grid-cols-3 gap-2 py-1">
                <Button size="sm" variant="secondary" onClick={() => void handleMockRoleLogin('customer')}>
                  Customer
                </Button>
                <Button size="sm" variant="secondary" onClick={() => void handleMockRoleLogin('staff')}>
                  Staff
                </Button>
                <Button size="sm" variant="secondary" onClick={() => void handleMockRoleLogin('admin')}>
                  Admin
                </Button>
              </div>
            ) : null}

            {navLinks.map((link) => (
              <Link
                key={`${link.href}-${link.label}`}
                href={link.href}
                className="block rounded-md px-3 py-2 text-sm font-semibold text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)]"
                onClick={handleMobileLinkClick}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
};

Navigation.displayName = 'Navigation';
