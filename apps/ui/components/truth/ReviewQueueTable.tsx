'use client';

import React from 'react';
import Link from 'next/link';
import { cn } from '../utils';
import { ConfidenceBadge } from './ConfidenceBadge';
import type { ReviewQueueItem } from '../../lib/types/api';

export type SortKey = 'confidence_asc' | 'confidence_desc' | 'date_asc' | 'date_desc';

export interface ReviewQueueTableProps {
  items: ReviewQueueItem[];
  sort: SortKey;
  onSortChange: (sort: SortKey) => void;
  className?: string;
}

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'confidence_asc', label: 'Confidence ↑ (lowest first)' },
  { value: 'confidence_desc', label: 'Confidence ↓ (highest first)' },
  { value: 'date_asc', label: 'Date ↑ (oldest first)' },
  { value: 'date_desc', label: 'Date ↓ (newest first)' },
];

export const ReviewQueueTable: React.FC<ReviewQueueTableProps> = ({
  items,
  sort,
  onSortChange,
  className,
}) => {
  return (
    <div className={cn('space-y-3', className)}>
      {/* Sort control */}
      <div className="flex items-center gap-2">
        <label
          htmlFor="review-sort"
          className="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap"
        >
          Sort by:
        </label>
        <select
          id="review-sort"
          value={sort}
          onChange={(e) => onSortChange(e.target.value as SortKey)}
          className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      {items.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 italic py-8 text-center">
          No pending review items.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                  Product
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                  Category
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                  Field
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                  Proposed Value
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                  Confidence
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                  Source
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                  Proposed At
                </th>
                <th scope="col" className="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <td className="px-4 py-3 text-gray-900 dark:text-white font-medium max-w-[200px] truncate">
                    {item.product_title}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{item.category}</td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300 capitalize">
                    {item.field_name.replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300 max-w-[180px] truncate">
                    {item.proposed_value}
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceBadge value={item.confidence} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{item.source}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">
                    {new Date(item.proposed_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/staff/review/${item.entity_id}`}
                      className="text-blue-600 dark:text-blue-400 hover:underline text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
                    >
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

ReviewQueueTable.displayName = 'ReviewQueueTable';
