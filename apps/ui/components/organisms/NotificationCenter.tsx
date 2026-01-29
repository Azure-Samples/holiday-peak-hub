/**
 * NotificationCenter Organism Component
 * Global notification/toast system
 */

import React from 'react';
import { FiX, FiCheck, FiAlertCircle, FiInfo, FiAlertTriangle } from 'react-icons/fi';
import { cn } from '../utils';
import type { BaseComponentProps, Variant } from '../types';

export interface Notification {
  id: string;
  title?: string;
  message: string;
  variant?: Extract<Variant, 'success' | 'error' | 'warning' | 'info'>;
  duration?: number;
  icon?: React.ReactNode;
}

export interface NotificationCenterProps extends BaseComponentProps {
  /** Array of notifications */
  notifications: Notification[];
  /** Position of notification center */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
  /** Dismiss notification handler */
  onDismiss: (id: string) => void;
  /** Max notifications to show */
  maxNotifications?: number;
}

const positionClasses = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-center': 'top-4 left-1/2 -translate-x-1/2',
  'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
};

const variantConfig = {
  success: {
    icon: FiCheck,
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-green-200 dark:border-green-800',
    iconColor: 'text-green-600 dark:text-green-400',
    textColor: 'text-green-900 dark:text-green-100',
  },
  error: {
    icon: FiAlertCircle,
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800',
    iconColor: 'text-red-600 dark:text-red-400',
    textColor: 'text-red-900 dark:text-red-100',
  },
  warning: {
    icon: FiAlertTriangle,
    bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
    borderColor: 'border-yellow-200 dark:border-yellow-800',
    iconColor: 'text-yellow-600 dark:text-yellow-400',
    textColor: 'text-yellow-900 dark:text-yellow-100',
  },
  info: {
    icon: FiInfo,
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-200 dark:border-blue-800',
    iconColor: 'text-blue-600 dark:text-blue-400',
    textColor: 'text-blue-900 dark:text-blue-100',
  },
};

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  notifications,
  position = 'top-right',
  onDismiss,
  maxNotifications = 5,
  className,
  testId,
  ariaLabel,
}) => {
  const displayedNotifications = notifications.slice(0, maxNotifications);

  React.useEffect(() => {
    displayedNotifications.forEach((notification) => {
      if (notification.duration) {
        const timer = setTimeout(() => {
          onDismiss(notification.id);
        }, notification.duration);

        return () => clearTimeout(timer);
      }
    });
  }, [displayedNotifications, onDismiss]);

  if (displayedNotifications.length === 0) {
    return null;
  }

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Notification center'}
      className={cn(
        'fixed z-50 flex flex-col gap-3',
        'max-w-sm w-full',
        positionClasses[position],
        className
      )}
    >
      {displayedNotifications.map((notification) => {
        const variant = notification.variant || 'info';
        const config = variantConfig[variant];
        const Icon = notification.icon ? null : config.icon;

        return (
          <div
            key={notification.id}
            role="alert"
            className={cn(
              'flex items-start gap-3 p-4 rounded-lg border shadow-lg',
              'animate-in slide-in-from-top-5 fade-in',
              config.bgColor,
              config.borderColor
            )}
          >
            {/* Icon */}
            {notification.icon || Icon ? (
              <div className={cn('flex-shrink-0', config.iconColor)}>
                {notification.icon || (Icon && <Icon className="w-5 h-5" />)}
              </div>
            ) : null}

            {/* Content */}
            <div className="flex-1 min-w-0">
              {notification.title && (
                <h4 className={cn('text-sm font-semibold mb-1', config.textColor)}>
                  {notification.title}
                </h4>
              )}
              <p className={cn('text-sm', config.textColor)}>
                {notification.message}
              </p>
            </div>

            {/* Close button */}
            <button
              onClick={() => onDismiss(notification.id)}
              className={cn(
                'flex-shrink-0 p-1 rounded hover:bg-black/5 dark:hover:bg-white/5',
                'transition-colors',
                config.iconColor
              )}
              aria-label="Dismiss notification"
            >
              <FiX className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};

NotificationCenter.displayName = 'NotificationCenter';

// Hook for managing notifications
export const useNotifications = () => {
  const [notifications, setNotifications] = React.useState<Notification[]>([]);

  const addNotification = React.useCallback((notification: Omit<Notification, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setNotifications((prev) => [...prev, { ...notification, id }]);
  }, []);

  const dismissNotification = React.useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearAll = React.useCallback(() => {
    setNotifications([]);
  }, []);

  return {
    notifications,
    addNotification,
    dismissNotification,
    clearAll,
  };
};
