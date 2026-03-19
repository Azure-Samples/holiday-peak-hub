import React, { useMemo } from 'react';
import { Chart } from '../atoms/Chart';
import type { AgentEvaluationTrend } from '@/lib/types/api';

export interface EvaluationTrendChartProps {
  trends: AgentEvaluationTrend[];
}

function normalizeTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString();
}

export const EvaluationTrendChart: React.FC<EvaluationTrendChartProps> = ({ trends }) => {
  const chartData = useMemo(() => {
    const pointMap = new Map<string, Record<string, number | string>>();

    for (const trend of trends) {
      for (const point of trend.points) {
        const timestampLabel = normalizeTimestamp(point.timestamp);
        const existing = pointMap.get(timestampLabel) ?? { timestamp: timestampLabel };
        existing[trend.metric] = point.value;
        pointMap.set(timestampLabel, existing);
      }
    }

    return Array.from(pointMap.values());
  }, [trends]);

  if (trends.length === 0 || chartData.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">No evaluation trend data available.</p>;
  }

  const colorPalette = ['var(--hp-primary)', 'var(--hp-accent)', 'var(--hp-text-muted)'];

  return (
    <Chart
      type="line"
      data={chartData}
      series={trends.map((trend, index) => ({
        dataKey: trend.metric,
        name: trend.metric,
        color: colorPalette[index % colorPalette.length],
      }))}
      xAxisKey="timestamp"
      height={300}
      showGrid
      showLegend
      showTooltip
    />
  );
};

EvaluationTrendChart.displayName = 'EvaluationTrendChart';
