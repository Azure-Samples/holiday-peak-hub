'use client';

import { useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Input } from '@/components/atoms/Input';
import { ReviewQueueTable, SortKey } from '@/components/truth/ReviewQueueTable';
import { useReviewQueue, useReviewStats } from '@/lib/hooks/useTruth';

const PAGE_SIZE = 20;

export default function StaffReviewQueuePage() {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState('');
  const [minConfidence, setMinConfidence] = useState('');
  const [maxConfidence, setMaxConfidence] = useState('');
  const [source, setSource] = useState('');
  const [sort, setSort] = useState<SortKey>('confidence_asc');

  const queryParams = {
    page,
    page_size: PAGE_SIZE,
    sort,
    ...(category && { category }),
    ...(minConfidence && { min_confidence: parseFloat(minConfidence) }),
    ...(maxConfidence && { max_confidence: parseFloat(maxConfidence) }),
    ...(source && { source }),
  };

  const { data, isLoading, isError } = useReviewQueue(queryParams);
  const { data: stats } = useReviewStats();

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              AI Review Queue
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Review AI-proposed product attribute changes.
            </p>
          </div>
          {stats && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-sm font-semibold">
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" aria-hidden="true" />
              {stats.pending} pending
            </span>
          )}
        </div>

        {/* Stats summary */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4">
              <p className="text-xs text-gray-500 dark:text-gray-400">Pending</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.pending}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-gray-500 dark:text-gray-400">Approved Today</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">{stats.approved_today}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-gray-500 dark:text-gray-400">Rejected Today</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">{stats.rejected_today}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-gray-500 dark:text-gray-400">Avg Confidence</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {Math.round(stats.avg_confidence * 100)}%
              </p>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Input
              name="category"
              type="text"
              placeholder="Filter by category"
              value={category}
              onChange={(e) => { setCategory(e.target.value); setPage(1); }}
              aria-label="Filter by category"
            />
            <Input
              name="min_confidence"
              type="number"
              placeholder="Min confidence (0–1)"
              value={minConfidence}
              min={0}
              max={1}
              step={0.05}
              onChange={(e) => { setMinConfidence(e.target.value); setPage(1); }}
              aria-label="Minimum confidence"
            />
            <Input
              name="max_confidence"
              type="number"
              placeholder="Max confidence (0–1)"
              value={maxConfidence}
              min={0}
              max={1}
              step={0.05}
              onChange={(e) => { setMaxConfidence(e.target.value); setPage(1); }}
              aria-label="Maximum confidence"
            />
            <Input
              name="source"
              type="text"
              placeholder="Filter by source"
              value={source}
              onChange={(e) => { setSource(e.target.value); setPage(1); }}
              aria-label="Filter by source"
            />
          </div>
        </Card>

        {/* Table */}
        {isLoading && (
          <Card className="p-6 text-gray-600 dark:text-gray-400">Loading review queue…</Card>
        )}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Review queue could not be loaded.
          </Card>
        )}

        {data && (
          <>
            <ReviewQueueTable
              items={data.items}
              sort={sort}
              onSortChange={(s) => { setSort(s); setPage(1); }}
            />

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Page {page} of {totalPages} ({data.total} items)
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(p - 1, 1))}
                    disabled={page <= 1}
                    className="px-3 py-1.5 rounded-md text-sm font-medium border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                    disabled={page >= totalPages}
                    className="px-3 py-1.5 rounded-md text-sm font-medium border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </MainLayout>
  );
}
