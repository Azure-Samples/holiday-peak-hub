"use client";

import React from 'react';
import Link from 'next/link';
import { Badge } from '../atoms/Badge';

export interface MenuItem {
  /** Display label */
  label: string;
  /** Navigation URL */
  href: string;
  /** Icon element */
  icon?: React.ReactNode;
  /** Optional badge count */
  badge?: {
    count: number;
    variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info' | 'light';
  };
  /** Active state */
  active?: boolean;
}

export interface MenuListProps {
  /** Array of menu items */
  items: MenuItem[];
  /** Optional title for the menu section */
  title?: string;
  /** Additional className for container */
  className?: string;
}

/**
 * MenuList Molecule Component
 * 
 * A vertical navigation menu with support for icons, badges, and active states.
 * Perfect for sidebar navigation, inbox categories, or any list-based navigation.
 * 
 * Features:
 * - Dark mode support
 * - Optional section title
 * - Icon support
 * - Badge counts
 * - Active state highlighting
 * - Accessible link navigation
 * 
 * @example
 * ```tsx
 * // Basic menu
 * <MenuList
 *   items={[
 *     { label: 'Dashboard', href: '/dashboard', icon: <FiHome /> },
 *     { label: 'Settings', href: '/settings', icon: <FiSettings /> },
 *   ]}
 * />
 * 
 * // Inbox menu with badges
 * <MenuList
 *   title="Mailbox"
 *   items={[
 *     {
 *       label: 'Inbox',
 *       href: '/inbox',
 *       icon: <FiInbox />,
 *       badge: { count: 12, variant: 'danger' },
 *     },
 *     {
 *       label: 'Sent',
 *       href: '/sent',
 *       icon: <FiMail />,
 *     },
 *     {
 *       label: 'Drafts',
 *       href: '/drafts',
 *       icon: <FiFile />,
 *       badge: { count: 3, variant: 'info' },
 *     },
 *   ]}
 * />
 * 
 * // With active state
 * <MenuList
 *   items={[
 *     { label: 'Home', href: '/', active: true },
 *     { label: 'About', href: '/about', active: false },
 *   ]}
 * />
 * ```
 */
export const MenuList: React.FC<MenuListProps> = ({
  items,
  title,
  className = '',
}) => {
  return (
    <div className={`flex flex-col w-full ${className}`}>
      {title && (
        <div className="flex flex-row items-center justify-start w-full p-2 text-xs font-normal tracking-wider uppercase text-gray-500 dark:text-gray-400">
          {title}
        </div>
      )}
      <nav className="flex flex-col w-full">
        {items.map((item, index) => (
          <Link
            key={index}
            href={item.href}
            className={`flex items-center justify-start w-full p-2 text-sm rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-800 ${
              item.active
                ? 'bg-gray-100 dark:bg-gray-800 font-semibold text-blue-600 dark:text-blue-400'
                : 'text-gray-700 dark:text-gray-300'
            }`}
          >
            {item.icon && (
              <span className="flex-shrink-0 w-5 h-5 mr-2">
                {item.icon}
              </span>
            )}
            <span className="flex-1">{item.label}</span>
            {item.badge && item.badge.count > 0 && (
              <Badge variant={item.badge.variant || 'primary'} size="sm">
                {item.badge.count}
              </Badge>
            )}
          </Link>
        ))}
      </nav>
    </div>
  );
};

MenuList.displayName = 'MenuList';

export default MenuList;
