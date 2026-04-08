/**
 * Card Molecule Component
 * Container component with header, body, and footer sections
 * Enhanced from components/Card.tsx
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface CardProps extends BaseComponentProps {
  /** Card content */
  children: React.ReactNode;
  /** Card title (renders in header) */
  title?: string;
  /** Card subtitle */
  subtitle?: string;
  /** Header content (overrides title/subtitle) */
  header?: React.ReactNode;
  /** Footer content */
  footer?: React.ReactNode;
  /** Card variant */
  variant?: 'default' | 'outlined' | 'elevated' | 'flat' | 'glass';
  /** Whether card has hover effect */
  hoverable?: boolean;
  /** Whether card is clickable */
  clickable?: boolean;
  /** Click handler for entire card */
  onClick?: () => void;
  /** Custom padding */
  padding?: 'none' | 'sm' | 'md' | 'lg';
  /** Whether to remove border radius */
  square?: boolean;
  /** Enable dynamic cursor glow effect */
  glowEffect?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  header,
  footer,
  variant = 'default',
  hoverable = false,
  clickable = false,
  onClick,
  padding = 'md',
  square = false,
  glowEffect = false,
  className,
  testId,
  ariaLabel,
}) => {
  const [mousePosition, setMousePosition] = React.useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = React.useState(false);
  const cardRef = React.useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!glowEffect || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    setMousePosition({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4 md:p-6',
    lg: 'p-6 md:p-8',
  };

  const variantClasses: Record<NonNullable<CardProps['variant']>, string> = {
    default: 'bg-white dark:bg-gray-900 shadow-sm border border-transparent',
    outlined: 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800',
    elevated: 'bg-white dark:bg-gray-900 shadow-xl border border-transparent',
    flat: 'bg-gray-50 dark:bg-zinc-900 border border-transparent',
    glass: 'bg-white/70 dark:bg-gray-900/40 backdrop-blur-xl border border-white/40 dark:border-white/10 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] dark:shadow-[0_8px_32px_0_rgba(0,0,0,0.3)]',
  };

  const hasHeader = title || subtitle || header;

  return (
    <div
      ref={cardRef}
      data-testid={testId}
      aria-label={ariaLabel}
      onClick={clickable ? onClick : undefined}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn(
        'relative w-full group overflow-hidden',
        variantClasses[variant],
        !square && 'rounded-2xl',
        (hoverable || clickable) &&
          'transition-all duration-500 ease-[cubic-bezier(0.25,1,0.5,1)] hover:-translate-y-1 hover:scale-[1.02] hover:shadow-[0_20px_40px_-10px_rgba(0,0,0,0.1)] dark:hover:shadow-[0_20px_40px_-10px_rgba(0,0,0,0.4)]',
        clickable && 'cursor-pointer active:scale-[0.98]',
        className
      )}
    >
      {/* Dynamic Glow Effect */}
      {glowEffect && isHovered && (
        <div
          className="pointer-events-none absolute -inset-px rounded-xl opacity-0 transition duration-300 group-hover:opacity-100"
          style={{
            background: `radial-gradient(600px circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(255,255,255,0.15), transparent 40%)`,
          }}
        />
      )}

      {/* SVG Micro-Interaction Decorative Element */}
      {hoverable && (
        <svg
          className="absolute -right-4 -top-4 w-24 h-24 text-gray-900/5 dark:text-white/5 opacity-0 group-hover:opacity-100 transition-all duration-700 ease-[cubic-bezier(0.25,1,0.5,1)] group-hover:scale-125 group-hover:-rotate-12 pointer-events-none"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z" />
        </svg>
      )}

      <div className="relative z-10 flex flex-col h-full">
        {hasHeader && (
          <div
            className={cn(
              'border-b border-gray-100 dark:border-gray-800/50 transition-colors duration-300',
              paddingClasses[padding]
            )}
          >
            {header || (
              <div className="flex flex-col gap-1">
                {title && (
                  <h3 className="text-xl md:text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100 transform transition-transform duration-300 group-hover:translate-x-1">
                    {title}
                  </h3>
                )}
                {subtitle && (
                  <p className="text-sm md:text-base font-medium text-gray-500 dark:text-gray-400">
                    {subtitle}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        <div className={cn('flex-grow', paddingClasses[padding])}>
          {children}
        </div>

        {footer && (
          <div
            className={cn(
              'mt-auto border-t border-gray-100 dark:border-gray-800/50 transition-colors duration-300 bg-gray-50/50 dark:bg-gray-800/20 backdrop-blur-sm',
              paddingClasses[padding]
            )}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

Card.displayName = 'Card';
