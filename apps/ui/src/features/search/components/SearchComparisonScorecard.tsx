'use client';

type SearchComparisonItem = {
  sku: string;
  score?: number;
};

type SearchComparisonScorecardProps = {
  intelligent: SearchComparisonItem[];
  keyword: SearchComparisonItem[];
  className?: string;
};

type ComparisonMetrics = {
  intelligentHits: number;
  keywordHits: number;
  intelligentAvgScore: number | null;
  keywordAvgScore: number | null;
  topOverlapCount: number;
  intelligentNoveltyCount: number;
};

function computeAverageScore(items: SearchComparisonItem[]): number | null {
  const scoredItems = items
    .map((item) => item.score)
    .filter((score): score is number => typeof score === 'number' && Number.isFinite(score));

  if (scoredItems.length === 0) {
    return null;
  }

  const total = scoredItems.reduce((acc, score) => acc + score, 0);
  return Number((total / scoredItems.length).toFixed(2));
}

function computeMetrics(
  intelligent: SearchComparisonItem[],
  keyword: SearchComparisonItem[],
): ComparisonMetrics {
  const topN = 5;
  const intelligentTop = intelligent.slice(0, topN).map((item) => item.sku);
  const keywordTopSet = new Set(keyword.slice(0, topN).map((item) => item.sku));

  const topOverlapCount = intelligentTop.filter((sku) => keywordTopSet.has(sku)).length;
  const intelligentNoveltyCount = intelligentTop.filter((sku) => !keywordTopSet.has(sku)).length;

  return {
    intelligentHits: intelligent.length,
    keywordHits: keyword.length,
    intelligentAvgScore: computeAverageScore(intelligent),
    keywordAvgScore: computeAverageScore(keyword),
    topOverlapCount,
    intelligentNoveltyCount,
  };
}

function formatAverageScore(value: number | null): string {
  if (value === null) {
    return 'N/A';
  }

  return value.toFixed(2);
}

export function SearchComparisonScorecard({
  intelligent,
  keyword,
  className,
}: SearchComparisonScorecardProps) {
  const metrics = computeMetrics(intelligent, keyword);

  const blocks = [
    {
      label: 'Top hits',
      value: `${metrics.intelligentHits} vs ${metrics.keywordHits}`,
      detail: 'intelligent vs keyword',
    },
    {
      label: 'Avg score',
      value: `${formatAverageScore(metrics.intelligentAvgScore)} vs ${formatAverageScore(metrics.keywordAvgScore)}`,
      detail: 'when scores are available',
    },
    {
      label: 'Top-5 novelty',
      value: `${metrics.intelligentNoveltyCount}`,
      detail: 'unique intelligent items',
    },
    {
      label: 'Top-5 overlap',
      value: `${metrics.topOverlapCount}`,
      detail: 'shared items across both',
    },
  ];

  return (
    <section
      aria-label="Intelligent versus keyword search scorecard"
      className={`rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] p-3 ${className ?? ''}`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">
        Search scorecard
      </p>
      <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {blocks.map((block) => (
          <div key={block.label} className="rounded-md border border-[var(--hp-border)] bg-[var(--hp-surface)] p-2">
            <p className="text-[11px] uppercase tracking-wide text-[var(--hp-text-muted)]">{block.label}</p>
            <p className="mt-1 text-sm font-semibold text-[var(--hp-text)]">{block.value}</p>
            <p className="mt-0.5 text-[11px] text-[var(--hp-text-muted)]">{block.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export type { SearchComparisonItem };