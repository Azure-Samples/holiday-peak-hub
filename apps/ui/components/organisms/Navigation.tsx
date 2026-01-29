/**
 * Navigation Organism Component
 * Main application navigation bar with Ocean Blue/Lime Green/Cyan theme
 */

import React from 'react';
import Link from 'next/link';
import { FiShoppingCart, FiHeart, FiUser, FiMenu, FiSearch } from 'react-icons/fi';
import { cn } from '../utils';
import { Button } from '../atoms/Button';
import { Badge } from '../atoms/Badge';
import { ThemeToggle } from '../atoms/ThemeToggle';
import { SearchInput } from '../molecules/SearchInput';
import { Dropdown, DropdownItem } from '../molecules/Dropdown';
import type { BaseComponentProps } from '../types';

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
    { label: 'Shop', href: '/shop' },
    { label: 'Categories', href: '/categories' },
    { label: 'Deals', href: '/deals' },
    { label: 'New Arrivals', href: '/new' },
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
  return (
    <nav
      data-testid={testId}
      aria-label={ariaLabel || 'Main navigation'}
      className={cn(
        'w-full z-50 transition-colors duration-200',
        sticky && 'sticky top-0',
        transparent
          ? 'bg-transparent'
          : 'bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800',
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Mobile Menu Button */}
          <div className="flex lg:hidden">
            <Button
              variant="ghost"
              size="sm"
              iconOnly
              onClick={onMobileMenuToggle}
              ariaLabel="Open menu"
            >
              <FiMenu className="w-6 h-6" />
            </Button>
          </div>

          {/* Logo */}
          <div className="flex-shrink-0">
            <Link href="/" className="flex items-center space-x-2">
              {logo || (
                <>
                  <div className="w-8 h-8 bg-ocean-500 dark:bg-ocean-300 rounded-lg flex items-center justify-center">
                    <FiShoppingCart className="w-5 h-5 text-white dark:text-gray-900" />
                  </div>
                  <span className="text-xl font-bold text-ocean-500 dark:text-ocean-300">
                    Holiday Peak
                  </span>
                </>
              )}
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <div className="hidden lg:flex lg:items-center lg:space-x-8">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-ocean-500 dark:hover:text-ocean-300 transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Search Bar (Desktop) */}
          <div className="hidden lg:flex flex-1 max-w-md mx-8">
            <SearchInput
              placeholder="Search products..."
              onSearch={onSearch}
              size="sm"
            />
          </div>

          {/* Right Actions */}
          <div className="flex items-center space-x-2">
            {/* Theme Toggle */}
            <ThemeToggle size="sm" />

            {/* Search Icon (Mobile) */}
            <div className="lg:hidden">
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                ariaLabel="Search"
              >
                <FiSearch className="w-5 h-5" />
              </Button>
            </div>

            {/* Wishlist */}
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

            {/* Cart */}
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
                    <Badge size="sm" className="bg-lime-500 text-white">
                      {cartCount}
                    </Badge>
                  </span>
                )}
              </Button>
            </Link>

            {/* User Menu */}
            {isLoggedIn ? (
              <Dropdown
                trigger={
                  userAvatar ? (
                    <img
                      src={userAvatar}
                      alt={userName || 'User'}
                      className="w-8 h-8 rounded-full"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-ocean-500 dark:bg-ocean-300 flex items-center justify-center text-white dark:text-gray-900 text-sm font-semibold">
                      {userName?.charAt(0)?.toUpperCase() || 'U'}
                    </div>
                  )
                }
                items={userMenuItems}
                placement="right"
                iconButton
              />
            ) : (
              <Button
                variant="primary"
                size="sm"
                iconLeft={<FiUser className="w-4 h-4" />}
                className="bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400"
              >
                <Link href="/login">Sign In</Link>
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-gray-200 dark:border-gray-800">
          <div className="px-4 py-3 space-y-1">
            {/* Mobile Search */}
            <div className="pb-3">
              <SearchInput
                placeholder="Search products..."
                onSearch={onSearch}
                size="sm"
              />
            </div>

            {/* Mobile Nav Links */}
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="block px-3 py-2 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md"
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
