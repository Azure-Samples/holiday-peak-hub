import React, { useMemo } from 'react';
import type { AgentTraceSpan } from '@/lib/types/api';

export interface TraceTimelineProps {
  spans: AgentTraceSpan[];
}

type TimelineNode = {
  span: AgentTraceSpan;
  depth: number;
};

function buildTimeline(spans: AgentTraceSpan[]): TimelineNode[] {
  const byParent = new Map<string, AgentTraceSpan[]>();
  const roots: AgentTraceSpan[] = [];

  for (const span of spans) {
    if (!span.parent_span_id) {
      roots.push(span);
      continue;
    }

    const siblings = byParent.get(span.parent_span_id) ?? [];
    siblings.push(span);
    byParent.set(span.parent_span_id, siblings);
  }

  const sortedRoots = [...roots].sort(
    (a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
  );

  const ordered: TimelineNode[] = [];

  const visit = (span: AgentTraceSpan, depth: number) => {
    ordered.push({ span, depth });
    const children = (byParent.get(span.span_id) ?? []).sort(
      (a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
    );

    for (const child of children) {
      visit(child, depth + 1);
    }
  };

  for (const root of sortedRoots) {
    visit(root, 0);
  }

  return ordered;
}

function statusClass(status: string): string {
  const normalized = status.toLowerCase();

  if (normalized === 'ok') {
    return 'text-green-700 dark:text-green-300';
  }

  if (normalized === 'warning') {
    return 'text-yellow-700 dark:text-yellow-300';
  }

  if (normalized === 'error') {
    return 'text-red-700 dark:text-red-300';
  }

  return 'text-gray-600 dark:text-gray-400';
}

export const TraceTimeline: React.FC<TraceTimelineProps> = ({ spans }) => {
  const orderedSpans = useMemo(() => buildTimeline(spans), [spans]);

  if (orderedSpans.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">No spans available.</p>;
  }

  return (
    <ul role="list" className="space-y-2">
      {orderedSpans.map(({ span, depth }) => (
        <li
          key={span.span_id}
          className="rounded-md border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900/40"
          style={{ marginLeft: `${depth * 0.75}rem` }}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">{span.name}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {span.service} · {Math.round(span.duration_ms)} ms
              </p>
            </div>
            <span className={`text-xs font-semibold uppercase tracking-wide ${statusClass(span.status)}`}>
              {span.status}
            </span>
          </div>
          {span.error_message && (
            <p className="mt-2 text-xs text-red-600 dark:text-red-400">{span.error_message}</p>
          )}
        </li>
      ))}
    </ul>
  );
};

TraceTimeline.displayName = 'TraceTimeline';
