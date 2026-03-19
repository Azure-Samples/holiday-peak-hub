import React, { useMemo } from 'react';
import type { AgentTraceSpan } from '@/lib/types/api';

export interface TraceWaterfallProps {
  spans: AgentTraceSpan[];
}

type WaterfallBar = {
  spanId: string;
  label: string;
  durationMs: number;
  leftPercent: number;
  widthPercent: number;
  status: string;
};

function statusBarClass(status: string): string {
  const normalized = status.toLowerCase();

  if (normalized === 'ok') {
    return 'bg-green-500';
  }

  if (normalized === 'warning') {
    return 'bg-yellow-500';
  }

  if (normalized === 'error') {
    return 'bg-red-500';
  }

  return 'bg-gray-500';
}

function buildBars(spans: AgentTraceSpan[]): WaterfallBar[] {
  if (spans.length === 0) {
    return [];
  }

  const sorted = [...spans].sort(
    (a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
  );

  const minStart = Math.min(...sorted.map((span) => new Date(span.started_at).getTime()));
  const maxEnd = Math.max(...sorted.map((span) => new Date(span.ended_at).getTime()));
  const totalDuration = Math.max(maxEnd - minStart, 1);

  return sorted.map((span) => {
    const start = new Date(span.started_at).getTime();
    const duration = Math.max(new Date(span.ended_at).getTime() - start, span.duration_ms, 1);

    return {
      spanId: span.span_id,
      label: span.name,
      durationMs: duration,
      leftPercent: ((start - minStart) / totalDuration) * 100,
      widthPercent: Math.max((duration / totalDuration) * 100, 1.5),
      status: span.status,
    };
  });
}

export const TraceWaterfall: React.FC<TraceWaterfallProps> = ({ spans }) => {
  const bars = useMemo(() => buildBars(spans), [spans]);

  if (bars.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">No timing data available.</p>;
  }

  return (
    <div className="space-y-2" role="list" aria-label="Trace timing waterfall">
      {bars.map((bar) => (
        <div key={bar.spanId} className="grid grid-cols-[minmax(120px,220px)_1fr] items-center gap-3" role="listitem">
          <span className="truncate text-xs text-gray-600 dark:text-gray-300" title={bar.label}>
            {bar.label}
          </span>
          <div className="relative h-5 rounded bg-gray-100 dark:bg-gray-800">
            <div
              className={`absolute top-0 h-5 rounded ${statusBarClass(bar.status)}`}
              style={{ left: `${bar.leftPercent}%`, width: `${bar.widthPercent}%` }}
              title={`${bar.durationMs.toFixed(0)} ms`}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

TraceWaterfall.displayName = 'TraceWaterfall';
