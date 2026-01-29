/**
 * Icon Atom Component
 * Wrapper for react-icons with standardized sizing
 */

import React from 'react';
import { cn, sizeClasses } from '../utils';
import type { Size, BaseComponentProps } from '../types';

export interface IconProps extends BaseComponentProps {
  /** Icon component from react-icons */
  icon: React.ComponentType<{ className?: string; size?: number }>;
  /** Icon size */
  size?: Size;
  /** Icon color (Tailwind class) */
  color?: string;
}

export const Icon: React.FC<IconProps> = ({
  icon: IconComponent,
  size = 'md',
  color,
  className,
  testId,
  ariaLabel,
}) => {
  return (
    <IconComponent
      className={cn(
        sizeClasses.icon[size],
        color,
        className
      )}
      data-testid={testId}
      aria-label={ariaLabel}
    />
  );
};

Icon.displayName = 'Icon';
