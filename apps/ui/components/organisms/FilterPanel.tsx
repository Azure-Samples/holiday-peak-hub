/**
 * FilterPanel Organism Component
 * Faceted search filters for e-commerce
 * Consolidates brands.tsx and categories.tsx patterns
 */

import React, { useState } from 'react';
import { FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { cn } from '../utils';
import { Checkbox } from '../atoms/Checkbox';
import { Radio } from '../atoms/Radio';
import { Button } from '../atoms/Button';
import { Divider } from '../atoms/Divider';
import type { FilterGroup, BaseComponentProps } from '../types';

export interface FilterPanelProps extends BaseComponentProps {
  /** Filter groups */
  filterGroups: FilterGroup[];
  /** Applied filters (filter id -> selected option ids) */
  selectedFilters?: Record<string, string[]>;
  /** Filter change handler */
  onFilterChange?: (filterId: string, optionId: string, checked: boolean) => void;
  /** Clear all filters handler */
  onClearAll?: () => void;
  /** Whether to show clear all button */
  showClearAll?: boolean;
  /** Whether groups are collapsible */
  collapsible?: boolean;
  /** Initially collapsed group ids */
  initialCollapsed?: string[];
  /** Whether to show counts */
  showCounts?: boolean;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filterGroups = [],
  selectedFilters = {},
  onFilterChange,
  onClearAll,
  showClearAll = true,
  collapsible = true,
  initialCollapsed = [],
  showCounts = true,
  className,
  testId,
  ariaLabel,
}) => {
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set(initialCollapsed)
  );

  const toggleGroup = (groupId: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  const isGroupCollapsed = (groupId: string) => collapsedGroups.has(groupId);

  const handleFilterChange = (groupId: string, optionId: string, checked: boolean) => {
    onFilterChange?.(groupId, optionId, checked);
  };

  const getTotalSelectedCount = () => {
    return Object.values(selectedFilters).reduce(
      (sum, filters) => sum + filters.length,
      0
    );
  };

  const totalSelected = getTotalSelectedCount();

  return (
    <aside
      data-testid={testId}
      aria-label={ariaLabel || 'Product filters'}
      className={cn('w-full', className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Filters
          {totalSelected > 0 && (
            <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
              ({totalSelected} selected)
            </span>
          )}
        </h3>

        {showClearAll && totalSelected > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearAll}
          >
            Clear all
          </Button>
        )}
      </div>

      {/* Filter Groups */}
      <div className="space-y-4">
        {filterGroups.map((group, index) => {
          const isCollapsed = collapsible && isGroupCollapsed(group.id);
          const groupSelections = selectedFilters[group.id] || [];

          return (
            <div key={group.id}>
              {index > 0 && <Divider spacing="sm" />}

              <div>
                {/* Group Header */}
                <button
                  type="button"
                  onClick={() => collapsible && toggleGroup(group.id)}
                  className={cn(
                    'w-full flex items-center justify-between py-2',
                    'text-left font-medium text-gray-900 dark:text-white',
                    collapsible && 'hover:text-blue-600 dark:hover:text-blue-400'
                  )}
                  aria-expanded={!isCollapsed}
                >
                  <span>
                    {group.label}
                    {groupSelections.length > 0 && (
                      <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
                        ({groupSelections.length})
                      </span>
                    )}
                  </span>

                  {collapsible && (
                    isCollapsed ? (
                      <FiChevronDown className="w-4 h-4" />
                    ) : (
                      <FiChevronUp className="w-4 h-4" />
                    )
                  )}
                </button>

                {/* Group Options */}
                {!isCollapsed && (
                  <div className="mt-2 space-y-2">
                    {group.type === 'checkbox' &&
                      group.options.map((option) => {
                        const isChecked = groupSelections.includes(option.id);

                        return (
                          <Checkbox
                            key={option.id}
                            name={`${group.id}-${option.id}`}
                            label={
                              <>
                                {option.label}
                                {showCounts && option.count !== undefined && (
                                  <span className="ml-1 text-xs text-gray-500 dark:text-gray-400">
                                    ({option.count})
                                  </span>
                                )}
                              </>
                            }
                            checked={isChecked}
                            onChange={(e) =>
                              handleFilterChange(group.id, option.id, e.target.checked)
                            }
                          />
                        );
                      })}

                    {group.type === 'radio' &&
                      group.options.map((option) => {
                        const isChecked = groupSelections.includes(option.id);

                        return (
                          <Radio
                            key={option.id}
                            name={group.id}
                            value={option.id}
                            label={
                              <>
                                {option.label}
                                {showCounts && option.count !== undefined && (
                                  <span className="ml-1 text-xs text-gray-500 dark:text-gray-400">
                                    ({option.count})
                                  </span>
                                )}
                              </>
                            }
                            checked={isChecked}
                            onChange={(e) =>
                              handleFilterChange(group.id, option.id, e.target.checked)
                            }
                          />
                        );
                      })}

                    {group.type === 'color' && (
                      <div className="flex flex-wrap gap-2">
                        {group.options.map((option) => {
                          const isChecked = groupSelections.includes(option.id);
                          const colorValue = option.value as string;

                          return (
                            <button
                              key={option.id}
                              type="button"
                              onClick={() =>
                                handleFilterChange(group.id, option.id, !isChecked)
                              }
                              className={cn(
                                'w-8 h-8 rounded-full border-2 transition-all',
                                isChecked
                                  ? 'border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800'
                                  : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                              )}
                              style={{ backgroundColor: colorValue }}
                              title={option.label}
                              aria-label={option.label}
                            />
                          );
                        })}
                      </div>
                    )}

                    {group.type === 'range' && (
                      <div className="px-2">
                        <input
                          type="range"
                          min={group.options[0]?.value as number}
                          max={group.options[group.options.length - 1]?.value as number}
                          className="w-full"
                        />
                        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                          <span>{group.options[0]?.label}</span>
                          <span>{group.options[group.options.length - 1]?.label}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
};

FilterPanel.displayName = 'FilterPanel';
