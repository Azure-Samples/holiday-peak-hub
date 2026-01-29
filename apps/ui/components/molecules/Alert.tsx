/**
 * Alert Molecule Component
 * Notification alert with icon, message, and close button
 * Migrated from components/alerts/index.tsx with enhancements
 */

import React, { useState } from 'react';
import { FiX, FiCheckCircle, FiAlertCircle, FiAlertTriangle, FiInfo } from 'react-icons/fi';
import { cn, variantClasses } from '../utils';
import type { Variant, BaseComponentProps } from '../types';

export interface AlertProps extends BaseComponentProps {
  /** Alert content */
  children: React.ReactNode;
  /** Alert variant */
  variant?: Variant;
  /** Alert title */
  title?: string;
  /** Custom icon (overrides default variant icon) */
  icon?: React.ReactNode;
  /** Whether to show icon */
  showIcon?: boolean;
  /** Whether alert can be dismissed */
  dismissible?: boolean;
  /** Callback when alert is dismissed */
  onDismiss?: () => void;
  /** Whether alert is outlined */
  outlined?: boolean;
  /** Whether alert has shadow */
  raised?: boolean;
  /** Whether alert has rounded corners */
  rounded?: boolean;
  /** Whether alert has left border accent */
  borderLeft?: boolean;
  /** Custom padding */
  padding?: 'sm' | 'md' | 'lg';
}

const variantIcons = {
  primary: FiInfo,
  secondary: FiInfo,
  success: FiCheckCircle,
  warning: FiAlertTriangle,
  error: FiAlertCircle,
  info: FiInfo,
  ghost: FiInfo,
};

export const Alert: React.FC<AlertProps> = ({
  children,
  variant = 'info',
  title,
  icon,
  showIcon = true,
  dismissible = true,
  onDismiss,
  outlined = false,
  raised = false,
  rounded = true,
  borderLeft = false,
  padding = 'md',
  className,
  testId,
  ariaLabel,
}) => {
  const [isVisible, setIsVisible] = useState(true);

  const handleDismiss = () => {
    setIsVisible(false);
    onDismiss?.();
  };

  if (!isVisible) return null;

  const IconComponent = variantIcons[variant];

  const paddingClasses = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel}
      role="alert"
      className={cn(
        'w-full flex items-start justify-start gap-3',
        paddingClasses[padding],
        outlined
          ? `border border-current ${variantClasses.alert[variant]}`
          : variantClasses.alert[variant],
        raised && 'shadow-md',
        rounded && 'rounded-lg',
        borderLeft && 'border-l-4 border-current',
        className
      )}
    >
      {showIcon && (
        <div className="shrink-0 mt-0.5">
          {icon || <IconComponent className="w-5 h-5" />}
        </div>
      )}

      <div className="flex-1 min-w-0">
        {title && (
          <h4 className="font-semibold mb-1">
            {title}
          </h4>
        )}
        <div className="text-sm">
          {children}
        </div>
      </div>

      {dismissible && (
        <button
          type="button"
          onClick={handleDismiss}
          className="shrink-0 ml-auto p-1 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          aria-label="Dismiss alert"
        >
          <FiX className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};

Alert.displayName = 'Alert';
