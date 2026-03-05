/**
 * Text Atom Component
 * Typography component for consistent text styling
 */

import React from 'react';
import { cn } from '../utils';
import type { Size, FontWeight, TextAlign, BaseComponentProps } from '../types';

type TextVariant = 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'p' | 'body' | 'span' | 'label' | 'caption';

export interface TextProps extends BaseComponentProps {
  /** Text content */
  children: React.ReactNode;
  /** Text variant (HTML element) */
  variant?: TextVariant;
  /** Text size */
  size?: Size;
  /** Font weight */
  weight?: FontWeight;
  /** Text alignment */
  align?: TextAlign;
  /** Text color (Tailwind class) */
  color?: string;
  /** Whether to truncate text with ellipsis */
  truncate?: boolean;
  /** Number of lines before truncating */
  lineClamp?: number;
  /** Whether text is uppercase */
  uppercase?: boolean;
  /** Whether text is italic */
  italic?: boolean;
}

const variantMap: Record<TextVariant, React.ElementType> = {
  h1: 'h1',
  h2: 'h2',
  h3: 'h3',
  h4: 'h4',
  h5: 'h5',
  h6: 'h6',
  p: 'p',
  body: 'p',
  span: 'span',
  label: 'label',
  caption: 'span',
};

const sizeMap: Record<Size, string> = {
  xs: 'text-xs',
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
  xl: 'text-xl',
};

const weightMap: Record<FontWeight, string> = {
  light: 'font-light',
  normal: 'font-normal',
  medium: 'font-medium',
  semibold: 'font-semibold',
  bold: 'font-bold',
};

const alignMap: Record<TextAlign, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
  justify: 'text-justify',
};

export const Text: React.FC<TextProps> = ({
  children,
  variant = 'p',
  size,
  weight = 'normal',
  align = 'left',
  color = 'text-gray-900 dark:text-white',
  truncate = false,
  lineClamp,
  uppercase = false,
  italic = false,
  className,
  testId,
  ariaLabel,
  ...props
}) => {
  const Component = variantMap[variant];
  const lineClampClass = typeof lineClamp === 'number' && lineClamp > 0
    ? `line-clamp-${lineClamp}`
    : undefined;

  // Default sizes for heading variants
  const defaultSize = variant === 'h1' ? 'xl' :
    variant === 'h2' ? 'xl' :
    variant === 'h3' ? 'lg' :
    variant === 'h4' ? 'lg' :
    variant === 'h5' ? 'md' :
    variant === 'h6' ? 'md' :
    variant === 'body' ? 'md' :
    variant === 'caption' ? 'xs' :
    'md';

  return (
    <Component
      data-testid={testId}
      aria-label={ariaLabel}
      className={cn(
        // Base color
        color,
        
        // Size
        sizeMap[size || defaultSize],
        
        // Weight
        weightMap[weight],
        
        // Alignment
        alignMap[align],
        
        // Truncation
        truncate && 'truncate',
        lineClampClass,
        
        // Text transforms
        uppercase && 'uppercase',
        italic && 'italic',
        
        // Custom classes
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
};

Text.displayName = 'Text';
