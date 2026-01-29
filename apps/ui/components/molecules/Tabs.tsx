/**
 * Tabs Molecule Component
 * Tabbed content navigation
 */

import React from 'react';
import { cn } from '../utils';
import type { BaseComponentProps } from '../types';

export interface Tab {
  id: string;
  label: React.ReactNode;
  content: React.ReactNode;
  disabled?: boolean;
  icon?: React.ReactNode;
}

export interface TabsProps extends BaseComponentProps {
  /** Array of tabs */
  tabs: Tab[];
  /** Currently active tab ID */
  activeTab?: string;
  /** Tab change handler */
  onTabChange?: (tabId: string) => void;
  /** Tabs orientation */
  orientation?: 'horizontal' | 'vertical';
  /** Tabs variant */
  variant?: 'line' | 'pills' | 'enclosed';
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab: controlledActiveTab,
  onTabChange,
  orientation = 'horizontal',
  variant = 'line',
  className,
  testId,
  ariaLabel,
}) => {
  const [internalActiveTab, setInternalActiveTab] = React.useState(tabs[0]?.id);
  
  const activeTab = controlledActiveTab !== undefined ? controlledActiveTab : internalActiveTab;

  const handleTabClick = (tabId: string) => {
    if (controlledActiveTab === undefined) {
      setInternalActiveTab(tabId);
    }
    onTabChange?.(tabId);
  };

  const activeContent = tabs.find(tab => tab.id === activeTab)?.content;

  const isHorizontal = orientation === 'horizontal';

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Tabs'}
      className={cn(
        'w-full',
        !isHorizontal && 'flex gap-4',
        className
      )}
    >
      {/* Tab List */}
      <div
        role="tablist"
        aria-orientation={orientation}
        className={cn(
          'flex',
          isHorizontal ? 'flex-row border-b border-gray-200 dark:border-gray-700' : 'flex-col',
          variant === 'pills' && 'gap-2',
          variant === 'line' && isHorizontal && 'gap-6',
          variant === 'line' && !isHorizontal && 'gap-2',
          !isHorizontal && 'min-w-[200px]'
        )}
      >
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`tabpanel-${tab.id}`}
              disabled={tab.disabled}
              onClick={() => !tab.disabled && handleTabClick(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                'dark:focus:ring-offset-gray-900',
                
                // Line variant
                variant === 'line' && [
                  isActive
                    ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                    : 'text-gray-600 dark:text-gray-400 border-b-2 border-transparent hover:text-gray-900 dark:hover:text-gray-200',
                  !isHorizontal && 'border-b-0 border-l-2',
                ],
                
                // Pills variant
                variant === 'pills' && [
                  'rounded-lg',
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800',
                ],
                
                // Enclosed variant
                variant === 'enclosed' && [
                  'border border-gray-200 dark:border-gray-700',
                  isActive
                    ? 'bg-white dark:bg-gray-800 border-b-white dark:border-b-gray-800 -mb-px'
                    : 'bg-gray-50 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800',
                  isHorizontal ? 'rounded-t-lg' : 'rounded-l-lg',
                ],
                
                tab.disabled && 'opacity-50 cursor-not-allowed',
                !tab.disabled && 'cursor-pointer'
              )}
            >
              {tab.icon && <span>{tab.icon}</span>}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panel */}
      <div
        id={`tabpanel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        className={cn(
          'flex-1',
          isHorizontal && 'mt-4',
          variant === 'enclosed' && isHorizontal && 'border border-gray-200 dark:border-gray-700 rounded-b-lg rounded-tr-lg p-4 -mt-px'
        )}
      >
        {activeContent}
      </div>
    </div>
  );
};

Tabs.displayName = 'Tabs';
